import typer
from src.ui.web import main as web_main
from src.ui.cli import main as cli_main

app = typer.Typer()

@app.command()
def web():
    """启动Web界面"""
    web_main()

@app.command()
def cli():
    """启动命令行界面"""
    cli_main()

if __name__ == "__main__":
    app() 