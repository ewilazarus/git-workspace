import typer

app = typer.Typer()


@app.command()
def convert(
    root: str | None = None,
    config_url: str | None = None,
) -> None:
    pass
