import typer

app = typer.Typer()


@app.command()
def path(
    branch: str,
    root: str | None = None,
) -> None:
    pass
