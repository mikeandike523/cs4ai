import os
import click

from utils.list_files import list_files as impl_list_files

# Default if neither place specifies anything
DEFAULT_REPO = True

@click.group()
@click.option(
    '--repo/--no-repo',
    default=None,  # None means "unspecified" so we can detect conflicts
    help='Repository mode (can also be set per subcommand).'
)
@click.pass_context
def cli(ctx, repo):
    """Top-level CLI group."""
    ctx.ensure_object(dict)
    # Store exactly what the user provided (True/False/None)
    ctx.obj['repo_global'] = repo


@cli.command()
@click.option(
    '--repo/--no-repo',
    'repo_local',
    default=None,  # None means "unspecified" at subcommand level
    help='Repository mode for this command.'
)
@click.pass_context
def list_files(ctx, repo_local):
    """List files, honoring global and per-command --repo flags with conflict check."""
    repo_global = ctx.obj.get('repo_global', None)

    # Conflict check: both specified and different → error
    if (repo_global is not None) and (repo_local is not None) and (repo_global != repo_local):
        raise click.UsageError(
            "Conflicting --repo settings: global is "
            f"{'--repo' if repo_global else '--no-repo'}, "
            f"but subcommand is {'--repo' if repo_local else '--no-repo'}."
        )

    # Resolve effective value (local overrides global; fall back to default)
    if repo_local is not None:
        effective_repo = repo_local
    elif repo_global is not None:
        effective_repo = repo_global
    else:
        effective_repo = DEFAULT_REPO

    files = impl_list_files(os.getcwd(), effective_repo)
    for file in files:
        print(file)


if __name__ == '__main__':
    cli(obj={})
