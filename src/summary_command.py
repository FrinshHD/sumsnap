import os
import re
import base64
from typing import Optional, List, Dict, Any
import typer
from rich.console import Console
from rich.markdown import Markdown
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
import openai
from openai.types.chat import ChatCompletionSystemMessageParam, ChatCompletionUserMessageParam
import chardet
import pathspec # Assume pathspec is always available
from PIL import Image

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
        # Accept any encoding detected, or fallback to extension check
        if result["encoding"]:
            return True
        # Fallback: treat common text file extensions as text
        text_exts = (".md", ".txt", ".py", ".js", ".json", ".yaml", ".yml", ".ini", ".cfg", ".toml", ".csv", ".rst")
        return file_path.lower().endswith(text_exts)
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

def _get_adjusted_gitignore_patterns(gitignore_abs_path: str, project_root_abs_path: str) -> List[str]:
    """
    Reads patterns from a .gitignore file and adjusts them to be relative to the project_root_abs_path.
    """
    adjusted_patterns = []
    gitignore_dir_abs = os.path.dirname(gitignore_abs_path)

    # Determine the prefix for patterns based on the .gitignore file's location
    if gitignore_dir_abs == project_root_abs_path:
        current_dir_prefix_for_patterns = ""
    else:
        current_dir_prefix_for_patterns = os.path.relpath(gitignore_dir_abs, project_root_abs_path).replace(os.sep, '/')
        if current_dir_prefix_for_patterns == ".": # Should be covered by the equality check above
            current_dir_prefix_for_patterns = ""

    with open(gitignore_abs_path, "r", encoding="utf-8") as f_gi:
        for line in f_gi:
            pattern_text = line.strip()
            if not pattern_text or pattern_text.startswith('#'):
                continue

            negation_prefix = "!" if pattern_text.startswith("!") else ""
            if negation_prefix:
                pattern_text = pattern_text[1:]
            
            # If pattern starts with '/', it's anchored to its .gitignore file's directory.
            # Otherwise, it can match anywhere in or below that directory.
            # Pathspec handles this if the pattern is correctly formed relative to the spec's root.
            
            if pattern_text.startswith('/'):
                pattern_text = pattern_text[1:] # Remove leading slash, as prefix will anchor it

            if current_dir_prefix_for_patterns:
                # Prepend the directory prefix. Ensure no double slashes if pattern_text was empty.
                # Pathspec expects forward slashes.
                if pattern_text:
                    full_pattern = f"{current_dir_prefix_for_patterns}/{pattern_text}"
                else: # Pattern was just '/' or ' / '
                    full_pattern = current_dir_prefix_for_patterns
            else: # Pattern from .gitignore in project root
                full_pattern = pattern_text

            adjusted_patterns.append(negation_prefix + full_pattern)
    return adjusted_patterns

def summarize_chunk(
    chunk: str,
    api_key: str,
    api_endpoint: str,
    model: str,
    detailed: bool,
    format_readme: bool, # Kept for consistency, as is_update=True implies README format
    is_update: bool = False,
    images: Optional[List[Dict[str, Any]]] = None
) -> str:
    if is_update:
        prompt = (
            "You are tasked with updating an existing README.md file. "
            "The content provided is structured as follows:\n"
            "EXISTING_README_CONTENT_BEGINS:\n"
            "[Content of the current README]\n"
            "EXISTING_README_CONTENT_ENDS.\n\n"
            "NEW_CONTENT_TO_INTEGRATE_BEGINS:\n"
            "[Newly summarized information from project files or a specific file]\n"
            "NEW_CONTENT_TO_INTEGRATE_ENDS.\n\n"
            "Your goal is to intelligently integrate the new information into the existing README structure. "
            "Preserve relevant existing sections and content. Update or add sections based on the new information. "
            "If the existing README content is empty or minimal, generate a comprehensive README based on the new content to integrate. "
            "The final output must be a single, coherent, and professional README.md file. "
            "Focus on clarity, accuracy, and completeness. "
        )
        if detailed:
            prompt += "Ensure the new sections and updates are thorough and provide in-depth explanations where appropriate for a technical audience. "
        prompt += "The entire output should be valid markdown content, suitable for a README.md file. Do not wrap the entire response in a markdown code block (e.g., starting with ```markdown)."

    elif format_readme:
        prompt = (
            "Write a professional README.md file for the following content. "
            "Include sections like Description, Features, Usage, and (if possible) Installation. "
        )
        if detailed:
            prompt += (
                "The README should be extended, in-depth, and detailed, suitable for a technical audience. "
                "Highlight structure, purpose, and key components. Infer project goals and usage if possible. "
            )
        prompt += "Only use information present in the text. The output should be raw markdown content, suitable for a README.md file. Do not wrap the entire response in a markdown code block (e.g., starting with ```markdown)."
    elif detailed:
        prompt = (
            "Write an extended, in-depth, and detailed markdown summary of the following content as if for a technical audience. "
            "Highlight structure, purpose, and key components. "
            "If possible, infer project goals and usage. "
            "Only use information present in the text. "
        )
        if images:
            prompt += "Also analyze any provided images and describe their content, purpose, and relevance to the project. "
        prompt += "Format as markdown. Do not wrap the entire response in a markdown code block unless the content itself is a code block."
    else:
        prompt = "Summarize the following content. Be concise and only use information present in the text."
        if images:
            prompt += " Also describe any provided images and their relevance."
        prompt += " Format as markdown. Do not wrap the entire response in a markdown code block unless the content itself is a code block."

    # Prepare the message content
    message_content = []
    
    # Add text content
    if chunk.strip():
        message_content.append({
            "type": "text",
            "text": chunk
        })
    
    # Add images if provided
    if images:
        for image_data in images:
            message_content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:{image_data['mime_type']};base64,{image_data['base64']}"
                }
            })

    messages = [
        ChatCompletionSystemMessageParam(role="system", content=prompt),
        ChatCompletionUserMessageParam(role="user", content=message_content)
    ]
    
    client = openai.OpenAI(api_key=api_key, base_url=api_endpoint)
    response = client.chat.completions.create(
        model=model,
        messages=messages
    )
    content = response.choices[0].message.content
    if content is not None:
        stripped_content = content.strip()
        lines = stripped_content.splitlines()
        
        # Mitigate common issue: AI wrapping the entire response in a markdown code block.
        if len(lines) >= 2:
            first_line_trimmed = lines[0].strip()
            last_line_trimmed = lines[-1].strip()

            is_common_wrapper_start = (
                first_line_trimmed == "```markdown" or 
                first_line_trimmed == "```"
            )
            is_common_wrapper_end = (last_line_trimmed == "```")

            if is_common_wrapper_start and is_common_wrapper_end:
                if len(lines) > 2:
                    return "\n".join(lines[1:-1]).strip()
                else:
                    # Handles cases like "```markdown\n```" (empty wrapped block).
                    return "" 
        
        return stripped_content
    else:
        return ""

def scan_project_files(project_path: str, exclude: Optional[List[str]] = None) -> tuple[List[str], List[str]]:
    """
    Scan project directory for text files and image files, excluding specified files/folders
    and respecting .gitignore rules.
    Returns tuple of (text_file_paths, image_file_paths)
    """
    if exclude is None:
        exclude_set = set()
    else:
        exclude_set = set(exclude)
    
    text_file_paths = []
    image_file_paths = []
    master_spec = None
    
    all_patterns = []
    # First pass: collect all patterns from all .gitignore files
    for current_root, _, current_files in os.walk(project_path, topdown=True):
        if ".gitignore" in current_files:
            gitignore_file_abs = os.path.join(current_root, ".gitignore")
            try:
                all_patterns.extend(_get_adjusted_gitignore_patterns(gitignore_file_abs, project_path))
            except Exception as e:
                console.print(f"[yellow]Warning: Could not parse .gitignore file at {gitignore_file_abs}: {e}[/yellow]")

    if all_patterns:
        # Pathspec's from_lines handles the order of patterns for negation correctly.
        master_spec = pathspec.PathSpec.from_lines('gitwildmatch', all_patterns)

    for root, dirs, files in os.walk(project_path, topdown=True):
        if master_spec:
            # To match directories, pathspec expects them to end with a slash
            dirs[:] = [
                d for d in dirs 
                if not master_spec.match_file(
                    os.path.relpath(os.path.join(root, d), project_path).replace(os.sep, '/') + '/'
                )
            ]

        dirs[:] = [
            d for d in dirs
            if not d.startswith('.') and 
               not (d.startswith('__') and d.endswith('__')) and
               d not in exclude_set
        ]
        
        for file in files:
            file_abs_path = os.path.join(root, file)
            
            if master_spec:
                path_to_check_for_gitignore = os.path.relpath(file_abs_path, project_path).replace(os.sep, '/')
                if master_spec.match_file(path_to_check_for_gitignore):
                    continue

            lower_file = file.lower()
            if (
                lower_file.endswith('.log') or
                lower_file.endswith('.cache') or
                file.startswith('.') or
                (file.startswith('__') and file.endswith('__')) or
                lower_file.startswith('license') or
                lower_file.startswith('licence') or
                lower_file.startswith('copying') or
                lower_file.startswith('readme') or 
                file in exclude_set
            ):
                continue
            
            # First check if it's a valid image file using PIL detection
            if is_image_file(file_abs_path) and validate_image_file(file_abs_path):
                image_file_paths.append(file_abs_path)
            elif is_text_file(file_abs_path):
                text_file_paths.append(file_abs_path)
                
    return text_file_paths, image_file_paths

def is_image_file(file_path: str) -> bool:
    """Check if a file is a supported image format by attempting to open it with PIL."""
    try:
        with Image.open(file_path) as img:
            # Just check if PIL can identify the format
            return img.format is not None
    except Exception:
        return False

def encode_image_to_base64(image_path: str) -> str:
    """Encode an image file to base64 string."""
    try:
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode('utf-8')
    except Exception as e:
        raise RuntimeError(f"Failed to encode image {image_path}: {e}")

def get_image_mime_type(file_path: str) -> str:
    """Get the MIME type for an image file by detecting its format."""
    try:
        with Image.open(file_path) as img:
            format_name = img.format
            if format_name:
                # Convert PIL format names to MIME types
                format_to_mime = {
                    'PNG': 'image/png',
                    'JPEG': 'image/jpeg',
                    'JPG': 'image/jpeg',
                    'GIF': 'image/gif',
                    'BMP': 'image/bmp',
                    'TIFF': 'image/tiff',
                    'WEBP': 'image/webp',
                    'ICO': 'image/x-icon',
                    'PPM': 'image/x-portable-pixmap',
                    'PGM': 'image/x-portable-graymap',
                    'PBM': 'image/x-portable-bitmap',
                    'EPS': 'image/eps',
                    'PDF': 'application/pdf'
                }
                return format_to_mime.get(format_name.upper(), 'image/jpeg')
    except Exception:
        pass
    # Fallback to jpeg if detection fails
    return 'image/jpeg'

def validate_image_file(file_path: str) -> bool:
    """Validate that an image file can be opened and processed."""
    try:
        with Image.open(file_path) as img:
            img.verify()
            # Re-open to get format info since verify() can corrupt the image object
            with Image.open(file_path) as img2:
                return img2.format is not None
    except Exception:
        return False

def summary(
    path: str = typer.Argument(
        ...,
        help="Path to a file or project directory to summarize. Supports text files and images."
    ),
    save_to_file: bool = typer.Option(
        False,
        "--save-to-file",
        help="Save the generated summary to a markdown file. This is ignored if --update-readme is used."
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
        help="Format the summary as a professional README.md file. Implied if --update-readme is used."
    ),
    exclude: Optional[List[str]] = typer.Option(
        None,
        "--exclude",
        help="Comma-separated list of files or folders to exclude from the summary.",
        callback=lambda v: v.split(",") if v else []
    ),
    update_readme_path: Optional[str] = typer.Option(
        None,
        "--update-readme",
        help="Path to an existing README.md file to update. If provided, --format-readme is implied and the output will be saved to this file."
    ),
    include_images: bool = typer.Option(
        True,
        "--include-images/--no-images",
        help="Include image files in the analysis (requires vision-capable AI model)."
    ),
    debug: bool = typer.Option(
        False,
        "--debug",
        help="Enable debug output, including the list of files used for summarization.",
        hidden=True 
    )
):
    """
    Summarize a file or project directory using AI, with options for saving, formatting, and updating an existing README.
    
    Supports both text files and images. Image analysis requires a vision-capable AI model (like GPT-4 Vision).
    """
    api_key, api_endpoint, default_model = load_api_config()
    use_model = model or default_model

    existing_readme_content: Optional[str] = None
    is_updating_readme = False
    effective_format_readme = format_readme
    
    processed_content_files: List[str] = []

    if update_readme_path:
        is_updating_readme = True
        effective_format_readme = True
        if not os.path.isfile(update_readme_path):
            console.print(f"[bold red]Error: Specified README for update '{update_readme_path}' not found.[/bold red]")
            raise typer.Exit(code=1)
        existing_readme_content = read_text_file(update_readme_path)
        if not existing_readme_content:
            existing_readme_content = "" 
            console.print(f"[bold yellow]Warning: Existing README '{update_readme_path}' is empty. A new README will be generated based on project/file content and saved to this path.[/bold yellow]")


    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
        console=console,
    ) as progress:
        final_summary = ""
        # These will store the actual text read from files/project to determine if content was processed
        project_text_content_processed = ""
        file_text_content_processed = ""
        project_images = []


        if os.path.isdir(path):
            scan_task = progress.add_task("[cyan]Scanning for files...", total=None)
            text_file_paths, image_file_paths = scan_project_files(path, exclude)
            # These are the files whose content will be attempted to be read and summarized
            processed_content_files = text_file_paths + image_file_paths
            progress.update(scan_task, completed=1); progress.remove_task(scan_task)

            if not text_file_paths and not image_file_paths and not (is_updating_readme and existing_readme_content and existing_readme_content.strip()):
                console.print(f"[bold red]No supported text or image files found in {path} to summarize, and no existing README to update (or it's empty).[/bold red]")
                raise typer.Exit(code=1)
            
            concat_task = progress.add_task(f"[cyan]Reading and processing files...", total=len(text_file_paths + image_file_paths) if (text_file_paths or image_file_paths) else None)
            project_text = ""
            project_images = []
            
            # Process text files
            if text_file_paths:
                for file_path_item in text_file_paths:
                    progress.update(concat_task, description=f"[cyan]Reading {os.path.relpath(file_path_item, path)}")
                    content = read_text_file(file_path_item)
                    if content.strip():
                        project_text += f"\n\n# FILE: {os.path.relpath(file_path_item, path)}\n\n{content}"
                    progress.advance(concat_task)
            
            # Process image files  
            if image_file_paths and include_images:
                for image_path in image_file_paths:
                    progress.update(concat_task, description=f"[cyan]Processing {os.path.relpath(image_path, path)}")
                    try:
                        base64_image = encode_image_to_base64(image_path)
                        mime_type = get_image_mime_type(image_path)
                        project_images.append({
                            'path': os.path.relpath(image_path, path),
                            'base64': base64_image,
                            'mime_type': mime_type
                        })
                        project_text += f"\n\n# IMAGE: {os.path.relpath(image_path, path)}\n\n[Image file - content will be analyzed by AI]\n"
                    except Exception as e:
                        console.print(f"[yellow]Warning: Could not process image {image_path}: {e}[/yellow]")
                    progress.advance(concat_task)
            elif image_file_paths and not include_images:
                console.print(f"[yellow]Note: Found {len(image_file_paths)} image file(s) but image processing is disabled. Use --include-images to analyze them.[/yellow]")
                    
            progress.remove_task(concat_task)
            project_text_content_processed = project_text # Store the concatenated text

            new_content_summary = ""
            if project_text_content_processed.strip() or project_images:
                chunk_task_new = progress.add_task("[cyan]Chunking new project text...", total=None)
                new_content_chunks = chunk_text(project_text) if project_text else [""]
                progress.update(chunk_task_new, completed=1); progress.remove_task(chunk_task_new)

                summarize_task_new = progress.add_task(f"[cyan]Summarizing {len(new_content_chunks)} new content chunk(s)...", total=len(new_content_chunks))
                new_content_summaries = []
                for idx, chunk_item in enumerate(new_content_chunks):
                    progress.update(summarize_task_new, description=f"[cyan]Summarizing new content chunk {idx+1}/{len(new_content_chunks)}")
                    # Include images only with the first chunk to avoid duplication
                    chunk_images = project_images if idx == 0 else None
                    # Summarize new content: detailed if requested, but don't apply README formatting or update logic at this stage
                    new_content_summaries.append(summarize_chunk(chunk_item, api_key, api_endpoint, use_model, detailed, False, is_update=False, images=chunk_images))
                    progress.advance(summarize_task_new)
                progress.remove_task(summarize_task_new)

                if len(new_content_summaries) > 1:
                    combine_task_new = progress.add_task("[cyan]Combining new content summaries...", total=None)
                    combined_new_summary_text = "\n\n".join(new_content_summaries)
                    new_content_summary = summarize_chunk(combined_new_summary_text, api_key, api_endpoint, use_model, detailed, False, is_update=False)
                    progress.update(combine_task_new, completed=1); progress.remove_task(combine_task_new)
                elif new_content_summaries:
                    new_content_summary = new_content_summaries[0]
            
            if is_updating_readme:
                if not new_content_summary.strip() and (not existing_readme_content or not existing_readme_content.strip()):
                    console.print(f"[bold red]Nothing to do: No new content from project and existing README ('{update_readme_path}') is empty.[/bold red]")
                    raise typer.Exit(code=1)
                if not new_content_summary.strip() and existing_readme_content and existing_readme_content.strip():
                     console.print(f"[bold yellow]Warning: No new content summarized from the project. The README at '{update_readme_path}' will be processed based on its existing content.[/bold yellow]")

                update_task = progress.add_task("[cyan]Updating README...", total=None)
                text_for_update = (
                    f"EXISTING_README_CONTENT_BEGINS:\n{existing_readme_content}\nEXISTING_README_CONTENT_ENDS.\n\n"
                    f"NEW_CONTENT_TO_INTEGRATE_BEGINS:\n{new_content_summary}\nNEW_CONTENT_TO_INTEGRATE_ENDS."
                )
                final_summary = summarize_chunk(text_for_update, api_key, api_endpoint, use_model, detailed, True, is_update=True)
                progress.update(update_task, completed=1); progress.remove_task(update_task)
            else: # Standard project summary (not updating an existing README)
                # This check might be redundant if the earlier check covers it
                if not project_text_content_processed.strip() and not project_images: 
                    console.print(f"[bold red]No readable content found in {path} to summarize.[/bold red]")
                    raise typer.Exit(code=1)
                final_summary = new_content_summary
                if effective_format_readme: # User explicitly asked for --format-readme (and not --update-readme)
                    readme_format_task = progress.add_task("[cyan]Formatting summary as README...", total=None)
                    final_summary = summarize_chunk(final_summary, api_key, api_endpoint, use_model, detailed, True, is_update=False)
                    progress.update(readme_format_task, completed=1); progress.remove_task(readme_format_task)

        elif os.path.isfile(path):
            # Check if it's an image file
            if is_image_file(path):
                if not include_images:
                    console.print(f"[bold red]Image file {path} provided but image processing is disabled. Use --include-images to analyze it.[/bold red]")
                    raise typer.Exit(code=1)
                    
                if not validate_image_file(path):
                    console.print(f"[bold red]Image file {path} appears to be corrupted or unsupported.[/bold red]")
                    raise typer.Exit(code=1)
                
                processed_content_files = [path]
                
                # Process the single image
                single_image = None
                try:
                    base64_image = encode_image_to_base64(path)
                    mime_type = get_image_mime_type(path)
                    single_image = [{
                        'path': os.path.basename(path),
                        'base64': base64_image,
                        'mime_type': mime_type
                    }]
                    file_text_content_processed = f"# IMAGE: {os.path.basename(path)}\n\n[Image file - content will be analyzed by AI]\n"
                except Exception as e:
                    console.print(f"[bold red]Failed to process image {path}: {e}[/bold red]")
                    raise typer.Exit(code=1)

                if is_updating_readme:
                    if not single_image and (not existing_readme_content or not existing_readme_content.strip()):
                        console.print(f"[bold red]Nothing to do: No image content from file '{os.path.basename(path)}' and existing README ('{update_readme_path}') is empty.[/bold red]")
                        raise typer.Exit(code=1)

                    update_task = progress.add_task("[cyan]Updating README with image...", total=None)
                    text_for_update = (
                        f"EXISTING_README_CONTENT_BEGINS:\n{existing_readme_content}\nEXISTING_README_CONTENT_ENDS.\n\n"
                        f"NEW_CONTENT_TO_INTEGRATE_BEGINS:\nAnalyze the provided image.\nNEW_CONTENT_TO_INTEGRATE_ENDS."
                    )
                    final_summary = summarize_chunk(text_for_update, api_key, api_endpoint, use_model, detailed, True, is_update=True, images=single_image)
                    progress.update(update_task, completed=1); progress.remove_task(update_task)
                else:
                    # Standard image analysis
                    analyze_task = progress.add_task("[cyan]Analyzing image...", total=None)
                    single_file_summary_content = summarize_chunk("Analyze and describe this image in detail.", api_key, api_endpoint, use_model, detailed, False, is_update=False, images=single_image)
                    progress.update(analyze_task, completed=1); progress.remove_task(analyze_task)
                    
                    final_summary = single_file_summary_content
                    if effective_format_readme:
                        readme_format_task = progress.add_task("[cyan]Formatting image analysis as README...", total=None)
                        final_summary = summarize_chunk(final_summary, api_key, api_endpoint, use_model, detailed, True, is_update=False)
                        progress.update(readme_format_task, completed=1); progress.remove_task(readme_format_task)
                        
            elif not is_text_file(path):
                console.print(f"[bold red]File {path} does not appear to be a text or image file.[/bold red]")
                raise typer.Exit(code=1)
            else:
                # This is a text file - existing logic
                processed_content_files = [path]

                file_text = read_text_file(path)
                file_text_content_processed = file_text # Store the read file text

                if not file_text_content_processed.strip() and not (is_updating_readme and existing_readme_content and existing_readme_content.strip()):
                    console.print(f"[bold red]File {path} is empty or unreadable, and no existing README to update (or it's empty).[/bold red]")
                    raise typer.Exit(code=1)

                single_file_summary_content = ""
                if file_text_content_processed.strip():
                    chunk_task = progress.add_task("[cyan]Chunking file text...", total=None)
                    chunks = chunk_text(file_text)
                    progress.update(chunk_task, completed=1); progress.remove_task(chunk_task)

                    summarize_task = progress.add_task(f"[cyan]Summarizing {len(chunks)} chunk(s)...", total=len(chunks))
                    summaries = []
                    for idx, chunk_item in enumerate(chunks):
                        progress.update(summarize_task, description=f"[cyan]Summarizing chunk {idx+1}/{len(chunks)}")
                        # Summarize file content: detailed if requested, but don't apply README formatting or update logic at this stage
                        summaries.append(summarize_chunk(chunk_item, api_key, api_endpoint, use_model, detailed, False, is_update=False))
                        progress.advance(summarize_task)
                    progress.remove_task(summarize_task)

                    if len(summaries) > 1:
                        combine_task = progress.add_task("[cyan]Combining chunk summaries...", total=None)
                        combined_summary_text = "\n\n".join(summaries)
                        single_file_summary_content = summarize_chunk(combined_summary_text, api_key, api_endpoint, use_model, detailed, False, is_update=False)
                        progress.update(combine_task, completed=1); progress.remove_task(combine_task)
                    elif summaries:
                        single_file_summary_content = summaries[0]
                
                if is_updating_readme:
                    if not single_file_summary_content.strip() and (not existing_readme_content or not existing_readme_content.strip()):
                        console.print(f"[bold red]Nothing to do: No content from file '{os.path.basename(path)}' and existing README ('{update_readme_path}') is empty.[/bold red]")
                        raise typer.Exit(code=1)
                    if not single_file_summary_content.strip() and existing_readme_content and existing_readme_content.strip():
                         console.print(f"[bold yellow]Warning: No content summarized from file '{os.path.basename(path)}'. The README at '{update_readme_path}' will be processed based on its existing content.[/bold yellow]")

                    update_task = progress.add_task("[cyan]Updating README...", total=None)
                    text_for_update = (
                        f"EXISTING_README_CONTENT_BEGINS:\n{existing_readme_content}\nEXISTING_README_CONTENT_ENDS.\n\n"
                        f"NEW_CONTENT_TO_INTEGRATE_BEGINS:\n{single_file_summary_content}\nNEW_CONTENT_TO_INTEGRATE_ENDS."
                    )
                    final_summary = summarize_chunk(text_for_update, api_key, api_endpoint, use_model, detailed, True, is_update=True)
                    progress.update(update_task, completed=1); progress.remove_task(update_task)
                else: # Standard file summary (not updating an existing README)
                    # This check might be redundant if the earlier `if not file_text.strip()` covers it
                    if not file_text.strip(): 
                        console.print(f"[bold red]File {path} is empty or unreadable.[/bold red]")
                        raise typer.Exit(code=1)
                    final_summary = single_file_summary_content
                    if effective_format_readme: # User explicitly asked for --format-readme (and not --update-readme)
                        readme_format_task = progress.add_task("[cyan]Formatting summary as README...", total=None)
                        final_summary = summarize_chunk(final_summary, api_key, api_endpoint, use_model, detailed, True, is_update=False)
                        progress.update(readme_format_task, completed=1); progress.remove_task(readme_format_task)

        else:
            console.print(f"[bold red]{path} is not a valid file or directory.[/bold red]")
            raise typer.Exit(code=1)

        summary_generated = bool(final_summary.strip())

        if not summary_generated:
            console.print(f"[bold yellow]No summary was generated.[/bold yellow]")
            # Continue to print files if any were processed, then exit

        # Attempt to derive a sensible name for the panel title from the input path or the summary's first heading
        detected_name = os.path.basename(os.path.abspath(path if os.path.isdir(path) else os.path.dirname(path) if os.path.isfile(path) else path))
        if os.path.isfile(path):
            detected_name = os.path.basename(path)

        match = re.search(r"^#\s+(.+)", final_summary, re.MULTILINE)
        if match:
            heading = match.group(1).strip()
            # Heuristic: if the first markdown heading is multi-word and not like a filename, use it as the detected name.
            if len(heading) > 2 and (' ' in heading or not re.match(r"^[a-zA-Z0-9_.-]+$", heading)):
                detected_name = heading
        
        title_prefix = "Updated README" if is_updating_readme else "Summary"
        panel_title = f"[bold]{title_prefix} of {detected_name}[/bold]"
        if is_updating_readme and update_readme_path: # Ensure update_readme_path is not None
            panel_title = f"[bold]Updated README: {update_readme_path}[/bold]"


        summary_markdown = Markdown(final_summary)
        summary_panel = Panel(
            summary_markdown,
            title=panel_title,
            border_style="none",
            padding=(1, 2),
        )
        console.print(summary_panel)

        if is_updating_readme:
            output_file = update_readme_path
            assert output_file is not None, "Output file path for README update must not be None"
            try:
                save_summary_to_file(final_summary, output_file)
                console.print(f"[green]README updated and saved to {output_file}[/green]")
            except Exception as e:
                console.print(f"[bold red]Failed to save updated README: {e}[/bold red]")
        elif save_to_file:
            if os.path.isdir(path):
                output_file = os.path.join(path, "project_summary.md")
            else: # path is a file
                output_file = os.path.splitext(path)[0] + "_summary.md"
            
            try:
                save_summary_to_file(final_summary, output_file)
                console.print(f"[green]Summary saved to {output_file}[/green]")
            except Exception as e:
                console.print(f"[bold red]Failed to save summary: {e}[/bold red]")

        # Print the list of files that were considered for summarization content if debug is enabled
        if debug and processed_content_files:
            console.print("\n[bold cyan]Content source files considered for summarization (debug):[/bold cyan]")
            abs_input_path = os.path.abspath(path)
            # Determine base path for making displayed paths relative and cleaner
            base_for_relpath = os.path.dirname(abs_input_path) if os.path.isfile(abs_input_path) else abs_input_path
            
            for f_path in processed_content_files:
                abs_f_path = os.path.abspath(f_path)
                try:
                    relative_path = os.path.relpath(abs_f_path, base_for_relpath)
                except ValueError: # Handles paths on different drives (Windows)
                    relative_path = abs_f_path # Fallback to absolute path
                console.print(f"- {relative_path}")
        
        if not summary_generated:
            raise typer.Exit(code=0) # Exit gracefully if no summary was generated