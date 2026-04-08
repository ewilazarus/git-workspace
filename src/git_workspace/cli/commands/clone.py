import typer

app = typer.Typer()


@app.command()
def clone(
    url: str,
    config_url: str | None = None,
    root: str | None = None,
) -> None:
    pass
