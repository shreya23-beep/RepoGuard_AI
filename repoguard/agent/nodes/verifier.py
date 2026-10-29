"""Verifier Node: Executes test suite in sandbox to validate the patch."""

import logging
from pathlib import Path
from typing import Any, Dict

from ...sandbox.runner import SandboxRunner
from ..state import RepoGuardState

logger = logging.getLogger("repoguard.verifier")


def verifier_node(state: RepoGuardState) -> Dict[str, Any]:
    """Sandbox verification state handler."""
    repo_path = Path(state.get("repo_path", ".")).resolve()
    test_command = state.get("test_command", "pytest")

    logger.info("Executing Verifier Node in %s (cmd: '%s')...", repo_path, test_command)

    runner = SandboxRunner(str(repo_path))
    result = runner.run_tests(test_command)

    logger.info(
        "Verification complete in %.2fs. Result: %s (Exit code: %d)",
        result.duration_seconds,
        "PASSED" if result.passed else "FAILED",
        result.exit_code,
    )

    return {
        "status": "verifying",
        "verification_passed": result.passed,
        "verification_logs": result.combined_output,
    }
