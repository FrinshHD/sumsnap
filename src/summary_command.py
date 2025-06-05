import os
import mimetypes
from dotenv import load_dotenv
from rich import print as rich_print
from rich.panel import Panel
from rich.markdown import Markdown
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import typer
from typing import Optional, Any, Iterator
import base64
import openai 

def summary(
    file_paths: list[str] = typer.Argument(..., help="Paths to files to summarize"),
    save_to_file: bool = False,
    model: Optional[str] = None,
    detailed: bool = typer.Option(False, "--detailed", help="Generate a longer, more detailed summary."),
):
    console = Console()
    processed_summaries_for_saving = []
    summary_results = []

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        task = progress.add_task(description="Processing files...", total=len(file_paths))
        for file_path in file_paths:
            progress.update(task, description=f"Summarizing [bold]{file_path}[/bold]...")
            current_summary_parts = []
            error_message = None
            try:
                for chunk_content in summarize_file(file_path, model_param=model, detailed=detailed):
                    if chunk_content:
                        current_summary_parts.append(chunk_content)
                full_summary_text = "".join(current_summary_parts)
                if not full_summary_text.strip():
                    full_summary_text = "_No summary content returned by the API._"
                summary_results.append((file_path, full_summary_text, None))
                if save_to_file:
                    processed_summaries_for_saving.append((file_path, full_summary_text))
            except ValueError as e:
                error_message = f"[bold red]Configuration error for {file_path}: {e}[/bold red]"
            except openai.APIError as e:
                error_message = f"[bold red]OpenAI API Error for {file_path}: {e}[/bold red]"
            except typer.Exit:
                raise
            except Exception as e:
                error_message = f"[bold red]Error summarizing {file_path}: {e}[/bold red]"
            if error_message:
                summary_results.append((file_path, None, error_message))
            progress.advance(task)

    # Now print results after the progress bar is gone
    for file_path, summary_text, error_message in summary_results:
        if error_message:
            console.print(error_message)
        else:
            rich_print_summary(summary_text, file_path)

    if save_to_file:
        for file_path, summary_text_content in processed_summaries_for_saving:
            save_summary_to_file(summary_text_content, file_path=file_path)

def rich_print_summary(summary_text: str, file_path: str):
    summary_markdown = Markdown(summary_text)
    summary_panel = Panel(
        summary_markdown,
        title=f"[bold]Summary of {file_path}[/bold]",
        border_style="none",
        padding=(1, 2),
    )
    rich_print(summary_panel)
    
def summarize_file(file_path: str, model_param: Optional[str] = None, detailed: bool = False) -> Iterator[str]:
    API_ENDPOINT = os.getenv("AI_API_ENDPOINT")
    API_KEY = os.getenv("AI_API_KEY")
    MODEL_NAME = model_param or os.getenv("AI_MODEL")

    if not API_KEY:
        raise ValueError("AI_API_KEY environment variable is not set. Please set it in your .env file or environment.")
    if not MODEL_NAME:
        raise ValueError("Model name must be specified. Use --model option or set AI_MODEL in .env file or environment.")
    
    try:
        client = openai.OpenAI(base_url=API_ENDPOINT, api_key=API_KEY)
    except Exception as e:
        raise typer.Exit(code=1)

    mime_type, _ = mimetypes.guess_type(file_path)
    is_text = mime_type and mime_type.startswith("text")

    user_message_content: Any

    try:
        if is_text:
            with open(file_path, "r", encoding="utf-8") as f:
                file_content_str = f.read()
            user_message_content = file_content_str
        else:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            b64_content = base64.b64encode(file_bytes).decode("utf-8")
            user_message_content = [
                {
                    "type": "text",
                    "text": "Analyze and summarize the content of the following file based on the detailed instructions provided in the system prompt."
                },
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:{mime_type or 'application/octet-stream'};base64,{b64_content}"
                    }
                }
            ]
    except Exception as e:
        raise Exception(f"Failed to read file {file_path}: {e}")

    system_prompt = (
        "Summarize the content of the following file. "
        "Only include information that is explicitly present in the file. "
        "Do not add, infer, or invent any information."
        "Do not include any information that is not present in the file."
        "The summary should be concise and to the point."
        "The summary should be in markdown format."
        "Do not include any fixes"
        "Create a summary that is not just a list of bullet points, but rather a coherent summary of the content."
        "If the file is an image, provide a brief description of the image content."
        "If the file is a text document, provide a summary of the main points."
        "If the file is a code file, provide a summary of the main functionality and purpose of the code."
        "If the file is a PDF, provide a summary of the main points and sections."
    )

    if detailed:
        system_prompt = (
            "Summarize the content of the following file in a detailed and comprehensive manner. "
            "Include all relevant information that is explicitly present in the file. "
            "Do not add, infer, or invent any information."
            "Do not include any information that is not present in the file."
            "The summary should be as detailed as possible, covering all main points and nuances. "
            "The summary should be in markdown format."
            "Do not include any fixes"
            "Create a summary that is not just a list of bullet points, but rather a coherent and thorough summary of the content."
            "If the file is an image, provide a detailed description of the image content."
            "If the file is a text document, provide a detailed summary of the main points."
            "If the file is a code file, provide a detailed summary of the main functionality and purpose of the code."
            "If the file is a PDF, provide a detailed summary of the main points and sections."
        )

    messages_for_openai = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message_content}
    ]
    
    try:
        completion_stream = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages_for_openai,
            stream=True
        )
        for chunk in completion_stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
    except openai.APIError as e:
        raise
    except Exception as e:
        raise
    
def save_summary_to_file(summary_text: str, file_path: str):
    output_file = f"{os.path.splitext(file_path)[0]}_summary.md"
    try:
        with open(output_file, "w", encoding="utf-8") as out_file:
            out_file.write(summary_text)
        rich_print(f"Summary saved to [cyan]{output_file}[/cyan]")
    except Exception as e:
        rich_print(f"[bold red]Error saving summary to file {output_file}: {e}[/bold red]")