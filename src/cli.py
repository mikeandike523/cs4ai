import os
import click

from utils.list_files import list_files as impl_list_files


@click.group()
@click.option(
    '--repo/--no-repo',
    default=True,
    help='Whether to operate in repository mode (default: --repo).'
)
@click.pass_context
def cli(ctx, repo):
    """Top-level CLI group."""
    # ensure ctx.obj is a dict so we can store global state
    ctx.ensure_object(dict)
    ctx.obj['repo'] = repo


@cli.command()
@click.pass_context
def list_files(ctx):
    """List files, respecting the --repo flag."""
    repo = ctx.obj.get('repo', True)
    

    files = impl_list_files(os.getcwd(), repo)
    for file in files:
        print(file)


if __name__ == '__main__':
    cli(obj={})
