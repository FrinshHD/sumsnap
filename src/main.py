import typer
import os
from dotenv import load_dotenv
from groq import Groq

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


if __name__ == "__main__":
    app()
