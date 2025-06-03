import typer
from dotenv import load_dotenv

from summary_command import summary

load_dotenv()  # Load .env variables

app = typer.Typer()

app.command("summary")(summary)

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
