import typer

app = typer.Typer()


@app.command("list")
@app.command("ls")
def list(
    root: str | None = None,
) -> None:
    pass
