import typer
from dotenv import load_dotenv

from summary_command import gemini_summary

load_dotenv()  # Load .env variables

app = typer.Typer()

app.command("gemini-summary")(gemini_summary)

@app.command()
def hello(name: str):
    print(f"Hello {name}")


@app.command()
def goodbye(name: str, formal: bool = False):
    if formal:
        print(f"Goodbye Ms. {name}. Have a good day.")
    else:
        print(f"Bye {name}!")

if __name__ == "__main__":
    app()
