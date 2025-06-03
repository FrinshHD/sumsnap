import os
import mimetypes
import requests
import json
from dotenv import load_dotenv
from rich import print as rich_print
from rich.panel import Panel
from rich.markdown import Markdown
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import typer
from typing import Optional
import base64

def summary(
    file_path: str,
    save_to_file: bool = False,
    output_file: str = "",
    model: Optional[str] = None,
):
    API_ENDPOINT = os.getenv("AI_API_ENDPOINT")
    API_KEY = os.getenv("AI_API_KEY")
    MODEL = model or os.getenv("AI_MODEL")
    if not API_ENDPOINT or not API_KEY:
        print("Error: AI_API_ENDPOINT and/or AI_API_KEY environment variables are not set.")
        raise typer.Exit(code=1)

    # Detect file type
    mime_type, _ = mimetypes.guess_type(file_path)
    is_text = mime_type and mime_type.startswith("text")

    try:
        if is_text:
            with open(file_path, "r", encoding="utf-8") as f:
                file_content = f.read()
            parts = [{"text": file_content}]
        else:
            with open(file_path, "rb") as f:
                file_bytes = f.read()
            b64_content = base64.b64encode(file_bytes).decode("utf-8")
            parts = [{
                "inline_data": {
                    "mime_type": mime_type or "application/octet-stream",
                    "data": b64_content
                }
            }]
    except Exception as e:
        print(f"Failed to read file: {e}")
        raise typer.Exit(code=1)

    prompt = (
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

    payload = {
        "model": MODEL,
        "contents": [
            {
                "parts": [{"text": prompt}] + parts
            }
        ]
    }
    endpoint = f"{API_ENDPOINT}{MODEL}:generateContent"
    params = {"key": API_KEY}
    headers = {"Content-Type": "application/json"}

    console = Console()
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console,
        ) as progress:
            progress.add_task(description="Generating summary...", total=None)
            response = requests.post(endpoint, params=params, headers=headers, data=json.dumps(payload))
        if response.status_code != 200:
            print(f"API Error: {response.status_code} {response.text}")
            raise typer.Exit(code=1)
        summary_text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        summary_markdown = Markdown(summary_text)
        summary_panel = Panel(
            summary_markdown,
            title="[bold]Summary[/bold]",
            border_style="none",
            padding=(1, 2),
        )
        rich_print(summary_panel)

        if save_to_file:
            if not output_file:
                output_file = f"{os.path.splitext(file_path)[0]}_summary.md"
            try:
                with open(output_file, "w") as out_file:
                    out_file.write(summary_text)
                print(f"Summary saved to {output_file}")
            except Exception as e:
                print(f"Failed to save summary: {e}")
                raise typer.Exit(code=1)
    except Exception as e:
        print(f"Error during AI API call: {e}")
        raise typer.Exit(code=1)