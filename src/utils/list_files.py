import os
from typing import List, Optional, Iterable, Tuple, Set
from dataclasses import dataclass
from gitignore_parser import parse_gitignore_str
from pathlib import Path
import posixpath


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


# --- New helper --------------------------------------------------------------
# Expand a list of *relative* directories (relative to CWD) into (a) the original
# leaves, and (b) the union of those leaves plus all ancestor directories needed
# to reach them.
# Example: ["src/app", "tests/unit"] ->
#   leaves={"src/app", "tests/unit"}
#   expanded={"src", "src/app", "tests", "tests/unit"}

def expand_with_ancestors(rel_dirs: Iterable[str]) -> Tuple[Set[str], Set[str]]:
    leaves: Set[str] = set()
    expanded: Set[str] = set()
    for d in rel_dirs:
        if not d:
            continue
        # Normalize and keep as POSIX-like relative strings (no leading ./)
        norm = os.path.normpath(d)
        if norm in (".", ""):
            # Including "." means unrestricted; represent it as empty sets handled by caller
            return set(), set()
        leaves.add(norm)
        parts = []
        for part in Path(norm).parts:
            parts.append(part)
            expanded.add(os.path.join(*parts))
    return leaves, expanded


def list_files(dirpath: str, repo: bool, included_dirs=tuple()) -> List[str]:
    """
    List files under `dirpath`, honoring .gitignore rules.

    If repo=True, walk from the repo root (dir containing .git) so top-level ignores apply,
    BUT only traverse toward `dirpath` and within its subtree. Results are reported
    relative to `dirpath`.

    If included_dirs is non-empty, restrict traversal to the union of those dirs *and
    their ancestors*, but only accept files that live within the original (leaf) dirs.
    This avoids prematurely pruning DFS branches while still returning only leaf hits.
    `included_dirs` entries are treated as paths relative to the current working dir.
    """
    dirpath_p = Path(dirpath).resolve()

    # Normalize included_dirs relative to CWD
    cwd_p = Path.cwd().resolve()
    included_dirs = tuple(os.path.normpath(d) for d in included_dirs)

    # Build (leaf, expanded-with-ancestors) rel-path sets
    leaf_rel, expanded_rel = expand_with_ancestors(included_dirs)

    # Convert to absolute Path sets (resolved from CWD)
    leaf_abs: Set[Path] = set((cwd_p / p).resolve() for p in leaf_rel) if leaf_rel else set()
    expanded_abs: Set[Path] = set((cwd_p / p).resolve() for p in expanded_rel) if expanded_rel else set()

    # --- Find repo root if requested
    repo_root: Optional[Path] = None
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

    # Membership checks -------------------------------------------------------
    def in_expanded(p: Path) -> bool:
        if not expanded_abs:
            return True  # no restriction
        return any(is_within(p, inc) for inc in expanded_abs)

    def in_leaf(p: Path) -> bool:
        if not leaf_abs:
            return True  # no restriction (mirrors previous behavior when included_dirs empty)
        return any(is_within(p, inc) for inc in leaf_abs)

    # Only traverse needed subtrees (repo constraint) + allow ancestors for included
    def should_descend(next_dir: Path) -> bool:
        ok_repo = True
        if repo and repo_root is not None:
            ok_repo = is_within(dirpath_p, next_dir) or is_within(next_dir, dirpath_p)

        ok_included = True
        if expanded_abs:  # use expanded to keep walking down toward leaves
            ok_included = any(
                is_within(inc, next_dir) or  # next_dir is an ancestor of an included leaf
                is_within(next_dir, inc)     # already within an included leaf subtree
                for inc in expanded_abs
            )
        return ok_repo and ok_included

    # Default reject — streamlined: enforce .git and expanded restriction globally
    def default_reject_fn(f: str) -> bool:
        p = Path(f).resolve()
        if p.name == ".git":
            return True
        # Allow ancestors to remain traversable, but still restrict to expanded set
        if not in_expanded(p):
            return True
        return False

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

        # Files: accept only within dirpath subtree (repo) AND within *leaf* set
        for file in files:
            abs_file = Path(current_dirpath, file).resolve()
            if not reject_fn(str(abs_file)):
                if (not (repo and repo_root is not None) or is_within(abs_file, dirpath_p)) and in_leaf(abs_file):
                    result.append(str(abs_file))

        # Folders: descend selectively (repo mode + included expanded)
        for folder in folders:
            next_dir = Path(current_dirpath, folder).resolve()
            if reject_fn(str(next_dir)):
                continue
            if should_descend(next_dir):
                recursion(str(next_dir), reject_fn)

    # If expanded set exists and doesn't intersect search_root, bail early
    if expanded_abs:
        intersects = any(is_within(inc, search_root) or is_within(search_root, inc) for inc in expanded_abs)
        if not intersects:
            return []

    recursion(str(search_root))

    # Present results relative to the original dirpath
    result = [os.path.relpath(f, str(dirpath_p)) for f in result]

    result = [os.path.normpath(f) for f in result]  # Just in case

    result = [f.replace("\\", "/") for f in result]  # Normalize to POSX-style paths

    return result
