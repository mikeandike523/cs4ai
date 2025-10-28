import os
from typing import Tuple
import click

from utils.list_files import list_files as impl_list_files
from utils.path_trees import paths_to_forest, render as render_tree
from utils.cli_ctx_helpers import (
    set_global_prop,
    get_global_prop,
    resolve_bool_flag,
)
from utils.format_file_readout import format_file_readout

# Default if neither place specifies anything
DEFAULT_REPO = True


@click.group()
@click.option(
    "--repo/--no-repo",
    default=None,  # None means "unspecified" so we can detect conflicts
    help="Repository mode (can also be set per subcommand).",
)
@click.pass_context
def cli(ctx, repo):
    """Top-level CLI group."""
    # Store exactly what the user provided (True/False/None)
    set_global_prop(ctx, "repo", repo)


def is_effective_child(parent_dir, child_path):
    return os.path.normpath(child_path).startswith(
        os.path.normpath(parent_dir)
    )

def get_files(effective_repo: bool, included_paths: Tuple[str]):
    included_dirs = []
    explict_included_dirs = []
    file_filters = []

    for included_path in included_paths:
        full_path = os.path.normpath(os.path.join(os.getcwd(), included_path))
        if os.path.isdir(full_path):
            included_dirs.append(os.path.normpath(included_path))
            explict_included_dirs.append(os.path.normpath(included_path))
        if os.path.isfile(full_path):
            # included_dirs.append(os.path.dirname(full_path))
            segments = os.path.normpath(included_path).split(os.path.sep)
            if len(segments) > 1:
                effective_parent = os.path.join(*segments[:-1])
                included_dirs.append(effective_parent)
            else:
                if "" not in included_dirs:
                    included_dirs.append("")
            file_filters.append(os.path.normpath(included_path))

    if any(os.path.isabs(dir_path) for dir_path in included_dirs):
        raise click.UsageError("Included directory paths must be relative.")
    
    files = impl_list_files(os.getcwd(), effective_repo, included_dirs)

    if len(file_filters) > 0:
        files = [
            f
            for f in files
            if os.path.normpath(f) in file_filters
            or any(dn and is_effective_child(dn, f) for dn in explict_included_dirs)
        ]

    return files

@cli.command()
@click.option(
    "--repo/--no-repo",
    "repo_local",
    default=None,  # None means "unspecified" at subcommand level
    help="Repository mode for this command.",
)
@click.option("--tree", is_flag=True, default=False, help="Show in a tree format.")
@click.argument("included_paths", type=str, nargs=-1)
@click.pass_context
def list_files(ctx, repo_local, tree, included_paths: Tuple[str]):
    """List files, honoring global and per-command --repo flags with conflict check."""
    repo_global = get_global_prop(ctx, "repo")

    # Resolve effective value (local overrides global; falls back to default) with conflict detection
    effective_repo = resolve_bool_flag(
        name="--repo",
        local_value=repo_local,
        global_value=repo_global,
        default=DEFAULT_REPO,
        true_label="--repo",
        false_label="--no-repo",
    )

   
    files = get_files(effective_repo, included_paths)


    if not tree:
        for file in files:
            print(file)
    else:
        forest = paths_to_forest(files, delimiter="/")
        for t in forest:
            print(render_tree(t))


@cli.command()
@click.option(
    "--repo/--no-repo",
    "repo_local",
    default=None,  # None means "unspecified" at subcommand level
    help="Repository mode for this command.",
)
@click.option(
    "-o", "--out-file", type=str, required=False, default=None, help="Output file path."
)
@click.argument("included_paths", type=str, nargs=-1)
@click.pass_context
def collect_files(ctx, repo_local, out_file, included_paths: Tuple[str]):
    """Collect project files into one readable bundle perfect for pasting into AI chatbot."""
    repo_global = get_global_prop(ctx, "repo")

    # Resolve effective value (local overrides global; falls back to default) with conflict detection
    effective_repo = resolve_bool_flag(
        name="--repo",
        local_value=repo_local,
        global_value=repo_global,
        default=DEFAULT_REPO,
        true_label="--repo",
        false_label="--no-repo",
    )

    files = get_files(effective_repo, included_paths)

    forest = paths_to_forest(files, delimiter="/")
    file_structure_readout = "\n".join(render_tree(t) for t in forest)

    sections = []

    sections.append(format_file_readout("File Structure", file_structure_readout))

    for file in files:
        full_path = os.path.join(os.getcwd(), os.path.normpath(file))
        try:
            with open(full_path, "r", encoding="utf-8") as f:
                file_content = f.read()
        except Exception as e:
            file_content = "<binary file or non-utf8 text>"
        sections.append(format_file_readout(file, file_content))

    if not out_file:

        print("\n\n".join(sections))

    else:

        with open(out_file, "w", encoding="utf-8", newline="\n") as f:
            f.write("\n\n".join(sections))


if __name__ == "__main__":
    cli(obj={})
