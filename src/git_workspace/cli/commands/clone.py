import typer

app = typer.Typer()


@app.command()
def clone(
    url: str,
    config_url: str | None = None,
    root: str | None = None,
) -> None:
    """
    Clone a repository into workspace format.

    Creates a new workspace root from a remote repository. The repository is cloned as a bare repository under .git, and a configuration repository is initialized under .workspace. This establishes the workspace structure required for managing branch worktrees.

    Use this when starting from an existing remote repository.
    """
    pass
