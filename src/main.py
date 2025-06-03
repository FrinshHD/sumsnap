import typer
from dotenv import load_dotenv

from summary_command import summary

load_dotenv()  # Load .env variables

app = typer.Typer()

app.command("summary")(summary)

@app.command()
def version():
    print("sumsnap v0.0.1")

if __name__ == "__main__":
    app()
