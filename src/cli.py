import os

import click

from utils.list_files import list_files as impl_list_files

@click.group()
def cli():
    pass

@cli.command()
def list_files():
    files = impl_list_files(os.getcwd())
    for file in files:
        print(file)


if __name__ == '__main__':
    cli()