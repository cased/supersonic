import click
from pathlib import Path
from typing import Optional, List, Tuple
import asyncio
import re

from granite import Granite
from granite.core.config import GraniteConfig


def validate_repo(ctx, param, value):
    """Validate repository format (owner/repo)"""
    if not re.match(r"^[^/]+/[^/]+$", value):
        raise click.BadParameter("Invalid repository format. Use owner/repo")
    return value


def validate_file(ctx, param, value):
    """Validate that file exists"""
    path = Path(value)
    if not path.exists():
        raise click.BadParameter(f"File not found: {value}")
    return value


@click.group()
@click.option("--token", envvar="GITHUB_TOKEN", help="GitHub token", required=True)
@click.pass_context
def cli(ctx: click.Context, token: str) -> None:
    """Granite - Rock-solid GitHub PR automation"""
    ctx.ensure_object(dict)
    ctx.obj = GraniteConfig(github_token=token)


@cli.command()
@click.argument("repo", callback=validate_repo)
@click.argument("file", callback=validate_file)
@click.argument("upstream_path", required=False)
@click.option("--title", help="PR title")
@click.option("--draft", is_flag=True, help="Create as draft PR")
@click.pass_obj
def update(
    config: GraniteConfig,
    repo: str,
    file: str,
    upstream_path: Optional[str],
    title: Optional[str],
    draft: bool,
) -> None:
    """Update a file in a repository"""
    try:
        granite = Granite(config)

        # Use local filename if no upstream path provided
        if not upstream_path:
            upstream_path = Path(file).name

        url = asyncio.run(
            granite.create_pr_from_file(
                repo=repo,
                local_file_path=file,
                upstream_path=upstream_path,
                title=title,
                draft=draft,
            )
        )
        click.echo(f"Created PR: {url}")
    except Exception as e:
        raise click.ClickException(f"Error: {str(e)}")


@cli.command()
@click.argument("repo")
@click.argument("content")
@click.argument("path")
@click.option("--title", help="PR title")
@click.option("--draft", is_flag=True, help="Create as draft PR")
@click.pass_obj
def update_content(
    config: GraniteConfig,
    repo: str,
    content: str,
    path: str,
    title: str,
    draft: bool,
) -> None:
    """Update a file with provided content"""
    granite = Granite(config)
    url = asyncio.run(
        granite.create_pr_from_content(
            repo=repo,
            content=content,
            path=path,
            title=title or f"Update {path}",
            draft=draft,
        )
    )
    click.echo(f"Created PR: {url}")


@cli.command()
@click.argument("repo", callback=validate_repo)
@click.option(
    "--file",
    "-f",
    multiple=True,
    nargs=2,
    help="File content and path (can be used multiple times)",
)
@click.option("--title", help="PR title")
@click.option("--draft", is_flag=True, help="Create as draft PR")
@click.pass_obj
def update_files(
    config: GraniteConfig,
    repo: str,
    file: List[Tuple[str, str]],
    title: Optional[str],
    draft: bool,
) -> None:
    """Update multiple files with provided content"""
    try:
        granite = Granite(config)

        # Read contents of local files
        files = {}
        for local_path, remote_path in file:
            try:
                content = Path(local_path).read_text()
                files[remote_path] = content
            except Exception as e:
                raise click.BadParameter(f"Failed to read file {local_path}: {e}")

        url = asyncio.run(
            granite.create_pr_from_files(
                repo=repo, files=files, title=title, draft=draft
            )
        )
        click.echo(f"Created PR: {url}")
    except Exception as e:
        raise click.ClickException(f"Error: {str(e)}")


if __name__ == "__main__":
    cli()
