"""
Git operations: clone, update, checkout latest commit.
"""
import os
from git import Repo


def clone_or_update(url: str, target_dir: str, filter_mode: str = "latest-cached"):
    """
    Clone or update a git repository.
    filter_mode: 'latest-commit' – checkout latest commit after pull,
                 'latest-cached' – keep whatever is checked out.
    """
    if os.path.exists(target_dir):
        # Update existing repo
        repo = Repo(target_dir)
        if repo.bare:
            # Not a valid repo, remove and reclone
            import shutil
            shutil.rmtree(target_dir)
            return clone_or_update(url, target_dir, filter_mode)
        # Fetch latest
        repo.remotes.origin.fetch()
        if filter_mode == "latest-commit":
            # Checkout latest commit on current branch
            repo.head.reset(commit='origin/HEAD', index=True, working_tree=True)
        else:
            # just pull
            repo.remotes.origin.pull()
    else:
        # Fresh clone
        os.makedirs(os.path.dirname(target_dir), exist_ok=True)
        repo = Repo.clone_from(url, target_dir)
        if filter_mode == "latest-commit":
            # Already at latest commit after clone
            pass
