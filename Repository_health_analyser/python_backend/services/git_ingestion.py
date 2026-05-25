"""
git_ingestion.py — Git repository walking using GitPython.

This module handles:
  1. Cloning a remote Git repository into a temporary local directory
  2. Walking every commit chronologically (oldest → newest)
  3. Extracting per-commit metadata: SHA, author, timestamp, message
  4. Extracting per-commit diffs: which files changed, lines added/removed
  5. Reading the raw file content at each commit for downstream parsing

Libraries used:
  - gitpython (git.Repo)  : Python wrapper around Git operations.
                            Cloning requires a working Git executable.
  - tempfile              : Creates a throw-away clone directory per ingestion run.
  - pathlib               : Cross-platform path handling.

Design notes:
  - Repos are cloned bare (no working tree) to save disk space.
  - Commits are walked in reverse topological order then reversed so index 0
    is the oldest commit (chronological order).
  - Diffs are computed against the first parent only (merge commits look at
    the mainline parent). This matches how `git log -p` works.
  - For performance on large repos, only the first `max_commits` are processed.
    The counter starts from the newest commit and works backwards, so you always
    get the most recent history.
"""

import os
import tempfile
import shutil
import logging
from dataclasses import dataclass, field
from typing import List, Optional, Iterator, Tuple
from datetime import datetime

import git  # pip install gitpython

logger = logging.getLogger(__name__)

# Spike detection threshold: if complexity grows by more than this percentage
# over the previous commit, flag as a spike commit.
SPIKE_THRESHOLD = 0.25   # 25%


@dataclass
class FileDiff:
    """
    Represents the change to a single file in a commit diff.

    Attributes:
        path         : File path relative to repo root (e.g. "src/auth/login.py")
        change_type  : 'A' added, 'D' deleted, 'M' modified, 'R' renamed
        lines_added  : Number of lines added in this file
        lines_removed: Number of lines removed in this file
        old_path     : Only set for renamed files ('R') — the original path
    """
    path: str
    change_type: str        # A | D | M | R
    lines_added: int = 0
    lines_removed: int = 0
    old_path: Optional[str] = None


@dataclass
class CommitInfo:
    """
    All metadata and diff information for a single commit.

    Attributes:
        sha          : Full 40-char commit hash
        short_sha    : First 8 characters (display use)
        message      : Full commit message
        author       : "Name <email>" string
        timestamp    : UTC datetime of the commit
        commit_index : 0-based position in chronological order
        files        : list of FileDiff objects for this commit
        total_added  : sum of lines_added across all files
        total_removed: sum of lines_removed across all files
        file_contents: dict mapping file_path → raw source text
                       (only populated for source-code files we can parse)
    """
    sha: str
    short_sha: str
    message: str
    author: str
    timestamp: datetime
    commit_index: int
    files: List[FileDiff] = field(default_factory=list)
    total_added: int = 0
    total_removed: int = 0
    file_contents: dict = field(default_factory=dict)


# File extensions we attempt to read content for (AST parsing)
PARSEABLE_EXTENSIONS = {".py", ".js", ".ts", ".jsx", ".tsx"}


def _safe_file_content(commit: git.Commit, path: str) -> Optional[str]:
    """
    Read the raw content of `path` at a specific git commit.
    Returns None if the file doesn't exist or can't be decoded as UTF-8.
    """
    try:
        blob = commit.tree[path]
        return blob.data_stream.read().decode("utf-8", errors="replace")
    except (KeyError, AttributeError, Exception):
        return None


def _parse_diff(diff_items) -> Tuple[List[FileDiff], int, int]:
    """
    Convert a GitPython diff into a list of FileDiff objects.

    Returns:
        (file_diffs, total_lines_added, total_lines_removed)
    """
    file_diffs: List[FileDiff] = []
    total_added = 0
    total_removed = 0

    for diff in diff_items:
        change_type = diff.change_type  # 'A', 'D', 'M', 'R'
        path = diff.b_path or diff.a_path
        old_path = diff.a_path if change_type == "R" else None

        added = 0
        removed = 0
        if diff.diff:
            # diff.diff is bytes — parse +/- line counts from unified diff
            try:
                diff_text = diff.diff.decode("utf-8", errors="replace")
                for line in diff_text.splitlines():
                    if line.startswith("+") and not line.startswith("+++"):
                        added += 1
                    elif line.startswith("-") and not line.startswith("---"):
                        removed += 1
            except Exception:
                pass

        file_diffs.append(FileDiff(
            path=path,
            change_type=change_type,
            lines_added=added,
            lines_removed=removed,
            old_path=old_path,
        ))
        total_added += added
        total_removed += removed

    return file_diffs, total_added, total_removed


def clone_repo(url: str, target_dir: str) -> git.Repo:
    """
    Clone the remote repository into `target_dir`.

    For public repos this is a standard HTTPS clone (no auth).
    The clone is full (not bare) so we can read file contents at each commit.

    Args:
        url        : HTTPS URL of the repo (e.g. "https://github.com/user/repo")
        target_dir : Local path to clone into (should be empty)

    Returns:
        git.Repo instance pointing at the cloned repo
    """
    git_executable = os.environ.get("GIT_PYTHON_GIT_EXECUTABLE") or shutil.which("git")
    if not git_executable:
        raise RuntimeError(
            "Git executable not found. Install Git and ensure `git --version` "
            "works in your terminal, then retry ingestion."
        )

    logger.info(f"Cloning {url} into {target_dir}")
    repo = git.Repo.clone_from(url, target_dir, depth=None)
    logger.info(f"Clone complete. HEAD: {repo.head.commit.hexsha[:8]}")
    return repo


def walk_commits(repo: git.Repo, max_commits: int = 500) -> Iterator[git.Commit]:
    """
    Walk commits from newest to oldest up to `max_commits`, then reverse.

    Yields commits in chronological order (oldest first, index 0 = oldest).
    This matches the way metrics should be graphed on a timeline.

    Args:
        repo        : Open git.Repo
        max_commits : Hard cap on number of commits to process
    """
    commits = list(repo.iter_commits("HEAD", max_count=max_commits))
    commits.reverse()  # chronological order
    for commit in commits:
        yield commit


def extract_commit_info(
    commit: git.Commit,
    index: int,
    parent: Optional[git.Commit] = None,
) -> CommitInfo:
    """
    Extract all metadata and diff information from a single commit.

    Args:
        commit  : The commit to inspect
        index   : Chronological position (0 = oldest)
        parent  : The immediately preceding commit (None for root commit)

    Returns:
        CommitInfo with metadata, diffs, and source file contents
    """
    sha = commit.hexsha
    short_sha = sha[:8]

    # Author as "Name <email>" — fall back gracefully
    try:
        author = f"{commit.author.name} <{commit.author.email}>"
    except Exception:
        author = "Unknown"

    # Timestamp: git stores as Unix epoch, convert to UTC datetime
    timestamp = datetime.utcfromtimestamp(commit.authored_date)

    # Message: strip excessive whitespace
    message = (commit.message or "").strip()[:500]

    # Compute diff vs parent
    if parent is not None:
        try:
            diff_index = parent.diff(commit, create_patch=True)
            file_diffs, total_added, total_removed = _parse_diff(diff_index)
        except Exception as e:
            logger.warning(f"Diff failed for {short_sha}: {e}")
            file_diffs, total_added, total_removed = [], 0, 0
    else:
        # Root commit: everything is "added"
        try:
            diff_index = commit.diff(git.NULL_TREE, create_patch=True)
            file_diffs, total_added, total_removed = _parse_diff(diff_index)
        except Exception:
            file_diffs, total_added, total_removed = [], 0, 0

    # Read file contents for parseable files (only from changed files)
    file_contents: dict = {}
    for fd in file_diffs:
        if fd.change_type != "D":  # skip deleted files
            ext = os.path.splitext(fd.path)[1].lower()
            if ext in PARSEABLE_EXTENSIONS:
                content = _safe_file_content(commit, fd.path)
                if content:
                    file_contents[fd.path] = content

    return CommitInfo(
        sha=sha,
        short_sha=short_sha,
        message=message,
        author=author,
        timestamp=timestamp,
        commit_index=index,
        files=file_diffs,
        total_added=total_added,
        total_removed=total_removed,
        file_contents=file_contents,
    )


def ingest_repository(
    url: str,
    max_commits: int = 500,
    progress_callback=None,
) -> Iterator[CommitInfo]:
    """
    Full pipeline: clone the repo, walk every commit, yield CommitInfo objects.

    This generator is consumed by the background ingestion worker. It handles
    its own temp-directory lifecycle — the clone is deleted when the generator
    is exhausted or closed.

    Args:
        url              : HTTPS URL of the public Git repo
        max_commits      : Maximum commits to process
        progress_callback: Optional callable(processed: int, total: int) for
                           progress reporting back to the DB

    Yields:
        CommitInfo for each commit, in chronological order

    Usage:
        for commit_info in ingest_repository("https://github.com/..."):
            store_commit(commit_info)
    """
    tmp_dir = tempfile.mkdtemp(prefix="repo_health_")
    try:
        repo = clone_repo(url, tmp_dir)

        # Collect commit list first so we know total count
        commits = list(walk_commits(repo, max_commits=max_commits))
        total = len(commits)
        logger.info(f"Processing {total} commits from {url}")

        previous: Optional[git.Commit] = None
        for idx, commit in enumerate(commits):
            info = extract_commit_info(commit, index=idx, parent=previous)
            if progress_callback:
                progress_callback(idx + 1, total)
            previous = commit
            yield info

    except Exception as e:
        logger.error(f"Ingestion failed for {url}: {e}")
        raise
    finally:
        # Always clean up the temp clone
        try:
            shutil.rmtree(tmp_dir, ignore_errors=True)
        except Exception:
            pass
