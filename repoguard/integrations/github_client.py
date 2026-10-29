"""GitHub API client and Git manager for RepoGuard AI."""

import logging
import os
import subprocess
from pathlib import Path
from typing import Optional
import httpx

from ..config import settings

logger = logging.getLogger("repoguard.github")


class GitHubIntegration:
    """Manages Git operations and GitHub REST API interactions."""

    def __init__(self, token: Optional[str] = None):
        self.token = token or settings.github_token
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "RepoGuard-AI-Agent",
        }
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"

    def clone_or_checkout(self, repo_url: str, branch: str, target_dir: Path) -> bool:
        """Clone repository or checkout specific PR branch."""
        try:
            if not target_dir.exists():
                logger.info("Cloning %s (%s) into %s...", repo_url, branch, target_dir)
                subprocess.run(
                    ["git", "clone", "--branch", branch, repo_url, str(target_dir)],
                    check=True,
                    capture_output=True,
                )
            else:
                logger.info("Checking out branch %s in %s...", branch, target_dir)
                subprocess.run(
                    ["git", "checkout", branch],
                    cwd=str(target_dir),
                    check=True,
                    capture_output=True,
                )
                subprocess.run(
                    ["git", "pull", "origin", branch],
                    cwd=str(target_dir),
                    check=False,
                    capture_output=True,
                )
            return True
        except Exception as e:
            logger.error("Git checkout failed: %s", e)
            return False

    def push_branch(self, repo_dir: Path, branch: str) -> bool:
        """Push committed fixes to the PR branch."""
        try:
            logger.info("Pushing healed commit to origin/%s...", branch)
            res = subprocess.run(
                ["git", "push", "origin", branch],
                cwd=str(repo_dir),
                capture_output=True,
                text=True,
            )
            return res.returncode == 0
        except Exception as e:
            logger.error("Git push failed: %s", e)
            return False

    def post_pr_comment(self, repo_full_name: str, pr_number: int, comment: str) -> bool:
        """Post the self-healing analysis and diff as a PR comment."""
        if not self.token:
            logger.warning("No GITHUB_TOKEN set. PR comment displayed locally only.")
            return False

        url = f"https://api.github.com/repos/{repo_full_name}/issues/{pr_number}/comments"
        try:
            with httpx.Client() as client:
                resp = client.post(
                    url,
                    headers=self.headers,
                    json={"body": comment},
                    timeout=15.0,
                )
                if resp.status_code in (200, 201):
                    logger.info("Successfully posted comment to PR #%d on %s", pr_number, repo_full_name)
                    return True
                else:
                    logger.error("Failed to post PR comment: %d %s", resp.status_code, resp.text)
                    return False
        except Exception as e:
            logger.error("Error communicating with GitHub API: %s", e)
            return False
