import os
from typing import Tuple
import click

from utils.list_files import list_files as impl_list_files
from utils.path_trees import paths_to_forest, render as render_tree

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
@click.option('--tree', is_flag=True, default=False, help='Show in a tree format.')
@click.argument('included_dirs', type=str, nargs=-1)
@click.pass_context
def list_files(ctx, repo_local, tree, included_dirs: Tuple[str]):
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

    if any(os.path.isabs(dir_path) for dir_path in included_dirs):
        raise click.UsageError(
            "Included directory paths must be relative."
        )

    files = impl_list_files(os.getcwd(), effective_repo, included_dirs)

    if not tree:
        for file in files:
            print(file)
    else:
        
        forest = paths_to_forest(files, delimiter="/")
        for t in forest:
            print(render_tree(t))



if __name__ == '__main__':
    cli(obj={})
