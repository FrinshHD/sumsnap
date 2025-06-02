import typer
import os
from dotenv import load_dotenv
from groq import Groq
from google import genai
from google.genai import types
import httpx
import mimetypes

load_dotenv()  # Load .env variables

app = typer.Typer()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:
    print("Error: GROQ_API_KEY environment variable is not set.")
    raise SystemExit(1)

client = Groq(api_key=GROQ_API_KEY)


@app.command()
def hello(name: str):
    print(f"Hello {name}")


@app.command()
def goodbye(name: str, formal: bool = False):
    if formal:
        print(f"Goodbye Ms. {name}. Have a good day.")
    else:
        print(f"Bye {name}!")


@app.command("ai-summary")
def ai_summary(file_path: str, model: str = "llama3-70b-8192"):

    try:
        with open(file_path, "r") as f:
            content = f.read()
    except Exception as e:
        print(f"Failed to read file: {e}")
        raise typer.Exit(code=1)

    messages = [
        {"role": "system", "content": "You are a helpful assistant that summarizes documents."},
        {"role": "user", "content": f"Please summarize the following document:\n\n{content}"}
    ]

    try:
        response = client.chat.completions.create(
            model=model,
            messages=messages
        )
        summary = response.choices[0].message.content
        print("\nSummary:\n" + summary)
    except Exception as e:
        print(f"Error during Groq API call: {e}")
        raise typer.Exit(code=1)

@app.command("gemini-summary")
def gemini_summary(file_path: str, model: str = "gemini-2.5-flash-preview-05-20"):
    try:
        with open(file_path, "rb") as f:
            doc_data = f.read()
    except Exception as e:
        print(f"Failed to read file: {e}")
        raise typer.Exit(code=1)

    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type:
        mime_type = "application/octet-stream"  # fallback

    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
    if not GOOGLE_API_KEY:
        print("Error: GOOGLE_API_KEY environment variable is not set.")
        raise typer.Exit(code=1)

    client = genai.Client(api_key=GOOGLE_API_KEY)
    prompt = "Summarize the content of the following file, don't add anything new:"

    try:
        response = client.models.generate_content(
            model=model,
            contents=[
                types.Part.from_bytes(
                    data=doc_data,
                    mime_type=mime_type,
                ),
                prompt
            ]
        )
        print("\nGemini Summary:\n" + response.text)
    except Exception as e:
        print(f"Error during Gemini API call: {e}")
        raise typer.Exit(code=1)

if __name__ == "__main__":
    app()
