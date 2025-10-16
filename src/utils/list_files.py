import os
from typing import List
from dataclasses import dataclass
from gitignore_parser import parse_gitignore_str
from pathlib import Path


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
                if entry.is_dir(follow_symlinks=True):
                    folderSymlinks.append(entry.name)
                elif entry.is_file(follow_symlinks=True):
                    fileSymlinks.append(entry.name)
                else:
                    # Broken symlink — keep with fileSymlinks
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


def list_files(dirpath: str, repo: bool) -> List[str]:
    """
    List files under `dirpath`, honoring .gitignore rules.
    If repo=True, walk from the repo root (dir containing .git) so top-level ignores apply,
    BUT only traverse toward `dirpath` and within its subtree. Results are reported
    relative to `dirpath`.
    """
    dirpath_p = Path(dirpath).resolve()

    # --- Find repo root if requested
    repo_root: Path | None = None
    if repo:
        p = dirpath_p
        while True:
            if (p / ".git").exists():  # works for .git folder or file
                repo_root = p
                break
            if p.parent == p:
                # reached filesystem root
                break
            p = p.parent

    # Where to start recursion for .gitignore propagation:
    search_root = repo_root if (repo and repo_root is not None) else dirpath_p

    # Helper path predicates (avoid Path.is_relative_to for 3.8 compatibility)
    def is_within(child: Path, parent: Path) -> bool:
        try:
            child.relative_to(parent)
            return True
        except ValueError:
            return False

    # Only traverse needed subtrees if starting at repo root:
    def should_descend(next_dir: Path) -> bool:
        if not (repo and repo_root is not None):
            return True
        # Descend if:
        #  - next_dir is an ancestor of dirpath_p (heading toward target subtree), OR
        #  - next_dir is within dirpath_p (already inside target subtree)
        return is_within(dirpath_p, next_dir) or is_within(next_dir, dirpath_p)

    def default_reject_fn(f: str) -> bool:
        # Always ignore the .git directory
        return os.path.basename(f) == ".git"

    result: List[str] = []

    def recursion(current_dirpath: str, last_fn=default_reject_fn):
        folder_items = get_folder_items(current_dirpath)
        files = folder_items.files
        folders = folder_items.folders

        # Compose .gitignore rules for this directory
        gitignore_path = os.path.join(current_dirpath, ".gitignore")
        if ".gitignore" not in folder_items.files:
            particular_reject_fn = default_reject_fn
        else:
            with open(gitignore_path, "r", encoding="utf-8", errors="ignore") as f:
                gitignore_text = f.read()
            particular_reject_fn = parse_gitignore_str(gitignore_text, base_dir=current_dirpath)

        reject_fn = lambda f: last_fn(f) or particular_reject_fn(f)

        # Files: add only those inside dirpath subtree (when repo mode is on)
        for file in files:
            abs_file = Path(current_dirpath, file).resolve()
            if not reject_fn(str(abs_file)):
                if not (repo and repo_root is not None) or is_within(abs_file, dirpath_p):
                    result.append(str(abs_file))

        # Folders: descend selectively when repo mode is on
        for folder in folders:
            next_dir = Path(current_dirpath, folder).resolve()
            if reject_fn(str(next_dir)):
                continue
            if should_descend(next_dir):
                recursion(str(next_dir), reject_fn)

    recursion(str(search_root))

    # Present results relative to the original dirpath
    result = [os.path.relpath(f, str(dirpath_p)) for f in result]

    return result