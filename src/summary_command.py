import os
import re
from typing import Optional, List
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
import openai
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
import chardet

import config

console = Console()

def load_api_config():
    api_endpoint = config.get_config("AI_API_ENDPOINT")
    api_key = config.get_config("AI_API_KEY")
    model = config.get_config("AI_MODEL")
    if not api_key or not api_endpoint or not model:
        raise RuntimeError("AI_API_KEY, AI_API_ENDPOINT, and AI_MODEL must be set in environment or .env file.")
    return api_key, api_endpoint, model

def is_text_file(file_path: str, blocksize: int = 512) -> bool:
    try:
        with open(file_path, "rb") as f:
            raw = f.read(blocksize)
        result = chardet.detect(raw)
        return result["encoding"] is not None and result["confidence"] > 0.7
    except Exception:
        return False

def read_text_file(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception:
        return ""

def chunk_text(text: str, max_tokens: int = 2000) -> List[str]:
    lines = text.splitlines()
    chunks = []
    chunk = []
    count = 0
    for line in lines:
        count += len(line.split())
        chunk.append(line)
        if count >= max_tokens:
            chunks.append("\n".join(chunk))
            chunk = []
            count = 0
    if chunk:
        chunks.append("\n".join(chunk))
    return chunks

def save_summary_to_file(summary_text: str, file_path: str):
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(summary_text)
    except Exception as e:
        raise RuntimeError(f"Failed to save summary: {e}")

def summarize_chunk(
    chunk: str,
    api_key: str,
    api_endpoint: str,
    model: str,
    detailed: bool,
    format_readme: bool
) -> str:
    prompt = "Summarize the following content. Be concise and only use information present in the text. Format as markdown."
    if detailed:
        prompt = (
            "Write an extended, in-depth, and detailed markdown summary of the following content as if for a technical audience. "
            "Highlight structure, purpose, and key components. "
            "If possible, infer project goals and usage. "
            "Only use information present in the text. "
            "Format as markdown."
        )
    if format_readme:
        prompt += (
            "\n\nFormat the summary as a professional README.md file, including sections like Description, Features, Usage, and (if possible) Installation."
        )

    messages = [
        ChatCompletionSystemMessageParam(role="system", content=prompt),
        ChatCompletionUserMessageParam(role="user", content=chunk)
    ]
    client = openai.OpenAI(api_key=api_key, base_url=api_endpoint)
    response = client.chat.completions.create(
        model=model,
        messages=messages
    )
    content = response.choices[0].message.content
    if content is not None:
        return content.strip()
    else:
        return ""

def scan_project_files(project_path: str, exclude: Optional[List[str]] = None) -> List[str]:
    """
    Scan project directory for text files, excluding specified files/folders.
    """
    if exclude is None:
        exclude_set = set()
    else:
        exclude_set = set(exclude)
    file_paths = []
    for root, dirs, files in os.walk(project_path):
        # Exclude folders in-place
        dirs[:] = [
            d for d in dirs
            if not d.startswith('.') and not (d.startswith('__') and d.endswith('__'))
            and d not in exclude_set
        ]
        for file in files:
            lower_file = file.lower()
            # Exclude files by name or pattern
            if (
                lower_file.endswith('.log')
                or lower_file.endswith('.cache')
                or file.startswith('.')
                or (file.startswith('__') and file.endswith('__'))
                or lower_file.startswith('license')
                or lower_file.startswith('licence')
                or lower_file.startswith('copying')
                or lower_file.startswith('readme')
                or file in exclude_set
            ):
                continue
            file_path = os.path.join(root, file)
            if is_text_file(file_path):
                file_paths.append(file_path)
    return file_paths

def summary(
    path: str = typer.Argument(
        ...,
        help="Path to a file or project directory to summarize."
    ),
    save_to_file: bool = typer.Option(
        False,
        "--save-to-file",
        help="Save the generated summary to a markdown file."
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model",
        help="Specify the model to use for summarization. Overrides the AI_MODEL environment variable."
    ),
    detailed: bool = typer.Option(
        False,
        "--detailed",
        help="Generate a longer, more detailed and in-depth summary."
    ),
    format_readme: bool = typer.Option(
        False,
        "--format-readme",
        help="Format the summary as a professional README.md file."
    ),
    exclude: Optional[List[str]] = typer.Option(
        None,
        "--exclude",
        help="Comma-separated list of files or folders to exclude from the summary.",
        callback=lambda v: v.split(",") if v else []
    ),
):
    """
    Summarize a file or project directory using AI, with options for saving and formatting.
    """
    api_key, api_endpoint, default_model = load_api_config()
    use_model = model or default_model

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        if os.path.isdir(path):
            # --- Project summary ---
            scan_task = progress.add_task("[cyan]Scanning for files...", total=None)
            file_paths = scan_project_files(path, exclude)
            progress.update(scan_task, completed=1)
            progress.remove_task(scan_task)

            if not file_paths:
                console.print(f"[bold red]No supported text files found in {path} to summarize.[/bold red]")
                raise typer.Exit(code=1)

            concat_task = progress.add_task(f"[cyan]Reading and concatenating {len(file_paths)} files...", total=len(file_paths))
            project_text = ""
            for file_path in file_paths:
                progress.update(concat_task, description=f"[cyan]Reading {os.path.relpath(file_path, path)}")
                content = read_text_file(file_path)
                if content.strip():
                    project_text += f"\n\n# FILE: {os.path.relpath(file_path, path)}\n\n{content}"
                progress.advance(concat_task)
            progress.remove_task(concat_task)

            if not project_text.strip():
                console.print(f"[bold red]No readable content found in {path}.[/bold red]")
                raise typer.Exit(code=1)

            chunk_task = progress.add_task("[cyan]Chunking project text...", total=None)
            chunks = chunk_text(project_text)
            progress.update(chunk_task, description=f"[cyan]Chunked into {len(chunks)} parts")
            progress.update(chunk_task, completed=1)
            progress.remove_task(chunk_task)

            summarize_task = progress.add_task(f"[cyan]Summarizing {len(chunks)} chunk(s)...", total=len(chunks))
            summaries = []
            for idx, chunk in enumerate(chunks):
                progress.update(summarize_task, description=f"[cyan]Summarizing chunk {idx+1}/{len(chunks)}")
                summaries.append(summarize_chunk(chunk, api_key, api_endpoint, use_model, detailed, format_readme))
                progress.advance(summarize_task)
            progress.remove_task(summarize_task)

            if len(summaries) > 1:
                combine_task = progress.add_task("[cyan]Combining chunk summaries...", total=None)
                combined_summary = "\n\n".join(summaries)
                progress.update(combine_task, description="[cyan]Generating final summary from all chunks")
                final_summary = summarize_chunk(combined_summary, api_key, api_endpoint, use_model, detailed, format_readme)
                progress.update(combine_task, completed=1)
                progress.remove_task(combine_task)
            else:
                final_summary = summaries[0]

            # Try to detect project name from summary, fallback to directory name
            project_dir_name = os.path.basename(os.path.abspath(path))
            detected_name = project_dir_name
            match = re.search(r"^#\s+(.+)", final_summary, re.MULTILINE)
            if match:
                heading = match.group(1).strip()
                if len(heading) > 2 and not re.match(r"^[a-zA-Z0-9_.-]+$", heading):
                    detected_name = heading

            summary_markdown = Markdown(final_summary)
            summary_panel = Panel(
                summary_markdown,
                title=f"[bold]Summary of {detected_name}[/bold]",
                border_style="none",
                padding=(1, 2),
            )
            console.print(summary_panel)

            if save_to_file:
                output_file = os.path.join(path, "project_summary.md")
                try:
                    save_summary_to_file(final_summary, output_file)
                    console.print(f"[green]Project summary saved to {output_file}[/green]")
                except Exception as e:
                    console.print(f"[bold red]Failed to save summary: {e}[/bold red]")

        elif os.path.isfile(path):
            # --- File summary ---
            if not is_text_file(path):
                console.print(f"[bold red]File {path} does not appear to be a text file.[/bold red]")
                raise typer.Exit(code=1)

            file_text = read_text_file(path)
            if not file_text.strip():
                console.print(f"[bold red]File {path} is empty or unreadable.[/bold red]")
                raise typer.Exit(code=1)

            chunk_task = progress.add_task("[cyan]Chunking file text...", total=None)
            chunks = chunk_text(file_text)
            progress.update(chunk_task, description=f"[cyan]Chunked into {len(chunks)} parts")
            progress.update(chunk_task, completed=1)
            progress.remove_task(chunk_task)

            summarize_task = progress.add_task(f"[cyan]Summarizing {len(chunks)} chunk(s)...", total=len(chunks))
            summaries = []
            for idx, chunk in enumerate(chunks):
                progress.update(summarize_task, description=f"[cyan]Summarizing chunk {idx+1}/{len(chunks)}")
                summaries.append(summarize_chunk(chunk, api_key, api_endpoint, use_model, detailed, format_readme))
                progress.advance(summarize_task)
            progress.remove_task(summarize_task)

            if len(summaries) > 1:
                combine_task = progress.add_task("[cyan]Combining chunk summaries...", total=None)
                combined_summary = "\n\n".join(summaries)
                progress.update(combine_task, description="[cyan]Generating final summary from all chunks")
                final_summary = summarize_chunk(combined_summary, api_key, api_endpoint, use_model, detailed, format_readme)
                progress.update(combine_task, completed=1)
                progress.remove_task(combine_task)
            else:
                final_summary = summaries[0]

            # Try to detect file name from summary, fallback to file name
            file_name = os.path.basename(path)
            detected_name = file_name
            match = re.search(r"^#\s+(.+)", final_summary, re.MULTILINE)
            if match:
                heading = match.group(1).strip()
                if len(heading) > 2 and not re.match(r"^[a-zA-Z0-9_.-]+$", heading):
                    detected_name = heading

            summary_markdown = Markdown(final_summary)
            summary_panel = Panel(
                summary_markdown,
                title=f"[bold]Summary of {detected_name}[/bold]",
                border_style="none",
                padding=(1, 2),
            )
            console.print(summary_panel)

            if save_to_file:
                output_file = os.path.splitext(path)[0] + "_summary.md"
                try:
                    save_summary_to_file(final_summary, output_file)
                    console.print(f"[green]File summary saved to {output_file}[/green]")
                except Exception as e:
                    console.print(f"[bold red]Failed to save summary: {e}[/bold red]")

        else:
            console.print(f"[bold red]{path} is not a valid file or directory.[/bold red]")
            raise typer.Exit(code=1)