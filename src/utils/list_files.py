import os
from typing import List
from dataclasses import dataclass
from gitignore_parser import parse_gitignore_str


@dataclass
class FolderItems:
    files: List[str]
    folders: List[str]
    fileSymlinks: List[str]
    folderSymlinks: List[str]
    # Hardlinks not need tracked as will operate as normal files or folders

def get_folder_items(dirpath: str) -> FolderItems:
    files = []
    folders = []
    fileSymlinks = []
    folderSymlinks = []

    with os.scandir(dirpath) as it:
        for entry in it:

            # Check symlinks first (is_dir/is_file follow links by default)
            if entry.is_symlink():
                # If the target exists and is a dir/file, classify accordingly.
                # For broken symlinks, both checks will be False; choose one bucket
                # or extend FolderItems to track broken links explicitly.
                if entry.is_dir(follow_symlinks=True):
                    folderSymlinks.append(entry.name)
                elif entry.is_file(follow_symlinks=True):
                    fileSymlinks.append(entry.name)
                else:
                    # Broken symlink — keep with fileSymlinks for now, or add a new field if you can.
                    fileSymlinks.append(entry.name)
                continue

            # Regular files/dirs (not symlinks)
            if entry.is_file(follow_symlinks=False):
                files.append(entry.name)
            elif entry.is_dir(follow_symlinks=False):
                folders.append(entry.name)
            else:
                # Special files (sockets, fifos, devices) are ignored here
                pass

    return FolderItems(files, folders, fileSymlinks, folderSymlinks)
def list_files(dirpath: str) -> List[str]:

    def default_reject_fn(f):
        if os.path.basename(f) == ".git":
            return True
        return False

    result = []

    def recursion(current_dirpath, last_fn = default_reject_fn):
        
        folder_items = get_folder_items(current_dirpath)

        files = folder_items.files
        folders = folder_items.folders

        if ".gitignore" not in folder_items.files:
            particular_reject_fn = default_reject_fn
        else:
            with open(os.path.join(current_dirpath, ".gitignore"), "r") as f:
                gitignore_text = f.read()
            particular_reject_fn = parse_gitignore_str(gitignore_text, base_dir=current_dirpath)

        reject_fn = lambda f: last_fn(f) or particular_reject_fn(f)

        for file in files:
            if not reject_fn(os.path.join(current_dirpath, file)):
                result.append(os.path.join(current_dirpath, file))
        for folder in folders:
            if not reject_fn(os.path.join(current_dirpath, folder)):
                recursion(os.path.join(current_dirpath, folder), reject_fn)

    recursion(dirpath)

    result = [os.path.relpath(f, dirpath) for f in result]

    return result
        
