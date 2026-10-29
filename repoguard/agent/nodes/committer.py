"""Committer & Reporter Node: Stages verified fixes and publishes PR comments."""

import logging
import subprocess
from pathlib import Path
from typing import Any, Dict

from ..state import RepoGuardState

logger = logging.getLogger("repoguard.committer")


def _format_pr_comment(state: RepoGuardState, healed: bool) -> str:
    """Format rich GitHub Markdown report for PR discussion."""
    attempt = state.get("current_attempt", 1)
    diagnostic = state.get("diagnostic", {})
    patch = state.get("proposed_patch", {})
    history = state.get("reflection_history", [])

    if healed:
        comment = [
            "## [RepoGuard AI] Self-Healing CI/CD Report",
            "",
            "> **Status**: **[PASSED] Verified & Healed**",
            f"> **Model**: `Llama-3-Nemotron-70B-Instruct` (Nebius AI Studio)",
            f"> **Reflection Cycles**: {len(history)} self-correction loops (Total attempts: {attempt})",
            "",
            "### [DIAGNOSIS]",
            f"- **Target File**: `{diagnostic.get('target_file')}`",
            f"- **Bug Category**: `{diagnostic.get('bug_type')}`",
            f"- **Root Cause**: {diagnostic.get('root_cause')}",
            "",
            "### [APPLIED PATCH]",
            f"{patch.get('explanation')}",
            "```python",
            f"{patch.get('fixed_code', '').strip()}",
            "```",
            "",
            "### [VERIFICATION SANDBOX]",
            "- Isolated test suite passed with returncode `0`.",
            "- Zero regressions detected across existing tests.",
        ]

        if history:
            comment.append("")
            comment.append("### [REFLECTION TRAJECTORY]")
            for h in history:
                comment.append(
                    f"- **Attempt {h.get('attempt')}**: Test suite failed -> "
                    f"Agent reflected: *{h.get('reflection_notes')}*"
                )

        comment.append("")
        comment.append("---")
        comment.append("*Autonomously diagnosed, patched, and verified by RepoGuard AI on Nebius GPU compute.*")
        return "\n".join(comment)
    else:
        comment = [
            "## [RepoGuard AI] CI/CD Triage Report",
            "",
            "> **Status**: **[WARNING] Manual Inspection Needed**",
            f"> **Model**: `Llama-3-Nemotron-70B-Instruct` (Nebius AI Studio)",
            f"> **Attempts Exhausted**: {attempt} iterations without green build.",
            "",
            "### [DIAGNOSIS]",
            f"- **Target File**: `{diagnostic.get('target_file')}`",
            f"- **Root Cause**: {diagnostic.get('root_cause')}",
            "",
            "### [REFLECTION HISTORY]",
        ]
        for h in history:
            comment.append(f"- **Attempt {h.get('attempt')}**: {h.get('reflection_notes')}")

        comment.append("")
        comment.append("---")
        comment.append("*RepoGuard AI refrained from pushing an unverified patch to safeguard the repository.*")
        return "\n".join(comment)


def committer_node(state: RepoGuardState) -> Dict[str, Any]:
    """Committer state handler."""
    repo_path = Path(state.get("repo_path", ".")).resolve()
    healed = state.get("verification_passed", False)
    diagnostic = state.get("diagnostic", {})
    patch = state.get("proposed_patch", {})

    report = _format_pr_comment(state, healed=healed)
    commit_sha = None

    if healed:
        logger.info("Fix verified! Creating git commit...")
        try:
            # Check if this is a git repo
            is_git = (repo_path / ".git").exists()
            if is_git:
                target_file = patch.get("target_file", "")
                commit_msg = (
                    f"fix(repoguard): resolve {diagnostic.get('bug_type', 'CI failure')} in {target_file}\n\n"
                    f"Autonomously patched and verified by RepoGuard AI (Llama-3-Nemotron-70B)."
                )
                subprocess.run(["git", "add", target_file], cwd=str(repo_path), check=False)
                res = subprocess.run(["git", "commit", "-m", commit_msg], cwd=str(repo_path), capture_output=True, text=True)
                if res.returncode == 0:
                    rev = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(repo_path), capture_output=True, text=True)
                    commit_sha = rev.stdout.strip()
                    logger.info("Committed fix: %s", commit_sha[:8])
        except Exception as e:
            logger.warning("Git commit skipped or failed: %s", e)

    return {
        "status": "healed" if healed else "failed",
        "commit_sha": commit_sha,
        "summary_report": report,
    }
