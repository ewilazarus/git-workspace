import typer

app = typer.Typer()


@app.command()
def prune(
    root: str | None = None,
) -> None:
    pass
