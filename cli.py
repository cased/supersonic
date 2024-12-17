import click
from pathlib import Path
from typing import Optional, List, Tuple
import asyncio

from granite import Granite
from granite.core.config import GraniteConfig


@click.group()
@click.option("--token", envvar="GITHUB_TOKEN", help="GitHub token")
@click.pass_context
def cli(ctx: click.Context, token: str) -> None:
    """Granite - Rock-solid GitHub PR automation"""
    ctx.ensure_object(dict)
    ctx.obj = GraniteConfig(github_token=token)


@cli.command()
@click.argument("repo")
@click.argument("file")
@click.argument("upstream_path", required=False)
@click.option("--title", help="PR title")
@click.option("--draft", is_flag=True, help="Create as draft PR")
@click.pass_obj
def update(
    config: GraniteConfig,
    repo: str,
    file: str,
    upstream_path: Optional[str],
    title: str,
    draft: bool,
) -> None:
    """Update a file in a repository"""
    granite = Granite(config)

    # Use local filename if no upstream path provided
    if not upstream_path:
        upstream_path = Path(file).name

    url = asyncio.run(
        granite.create_pr_from_file(
            repo=repo,
            file_path=file,
            upstream_path=upstream_path,
            title=title or f"Update {upstream_path}",
            draft=draft,
        )
    )
    click.echo(f"Created PR: {url}")


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
@click.argument("repo")
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
    title: str,
    draft: bool,
) -> None:
    """Update multiple files with provided content"""
    granite = Granite(config)

    # Convert file tuples to dict
    files = {path: content for content, path in file}

    url = asyncio.run(
        granite.create_pr_from_files(
            repo=repo,
            files=files,
            title=title or f"Update {len(files)} files",
            draft=draft,
        )
    )
    click.echo(f"Created PR: {url}")


if __name__ == "__main__":
    cli()
