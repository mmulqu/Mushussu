import git
import os
import subprocess
from typing import List

class GitError(Exception):
    """Custom exception for Git-related errors."""
    pass

def is_git_repo(path: str) -> bool:
    """Check if a given path is a Git repository."""
    try:
        _ = git.Repo(path)
        return True
    except git.InvalidGitRepositoryError:
        return False

def get_repo(path: str = '.') -> git.Repo:
    """Gets the Git repo object for a given path, raising an error if not found."""
    try:
        return git.Repo(path, search_parent_directories=True)
    except git.InvalidGitRepositoryError:
        raise GitError(f"'{os.path.abspath(path)}' is not a valid Git repository.")

def has_changes(repo_path: str = '.') -> bool:
    """Check if there are any uncommitted changes (including untracked files)."""
    repo = get_repo(repo_path)
    return repo.is_dirty(untracked_files=True)

def git_pull(repo_path: str = '.') -> str:
    """Perform a git pull in the specified repository."""
    try:
        repo = get_repo(repo_path)
        origin = repo.remotes.origin
        # Use subprocess for better output control and to handle credentials if needed
        result = subprocess.run(
            ['git', 'pull'],
            cwd=repo.working_dir,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except git.GitCommandError as e:
        raise GitError(f"Git pull failed: {e.stderr}")
    except subprocess.CalledProcessError as e:
        raise GitError(f"Git pull failed: {e.stderr}")


def git_add(files: List[str], repo_path: str = '.') -> None:
    """Add specified files to the staging area."""
    try:
        repo = get_repo(repo_path)
        repo.index.add(files)
    except git.GitCommandError as e:
        raise GitError(f"Git add failed: {e}")

def git_commit(message: str, repo_path: str = '.') -> str:
    """Commit the staged changes."""
    try:
        repo = get_repo(repo_path)
        commit = repo.index.commit(message)
        return commit.hexsha
    except git.GitCommandError as e:
        raise GitError(f"Git commit failed: {e}")

def git_push(repo_path: str = '.') -> str:
    """Push commits to the origin remote."""
    try:
        repo = get_repo(repo_path)
        origin = repo.remotes.origin
        # Use subprocess for better output control and to handle credentials if needed
        result = subprocess.run(
            ['git', 'push'],
            cwd=repo.working_dir,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except git.GitCommandError as e:
        raise GitError(f"Git push failed: {e.stderr}")
    except subprocess.CalledProcessError as e:
        raise GitError(f"Git push failed: {e.stderr}")

def get_git_revision_hash(repo_path: str = '.') -> str:
    """Gets the short hash of the current git HEAD."""
    try:
        repo = get_repo(repo_path)
        return repo.head.object.hexsha[:7]
    except Exception:
        return "unknown"

