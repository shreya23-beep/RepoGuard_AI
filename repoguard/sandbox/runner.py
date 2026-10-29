"""Execution sandbox for running tests and verifying patches safely."""

import os
import subprocess
import time
import shutil
from pathlib import Path
from typing import Dict, Optional
from pydantic import BaseModel

from ..config import settings


class ExecutionResult(BaseModel):
    """Result from a sandbox test run."""
    exit_code: int
    passed: bool
    stdout: str
    stderr: str
    combined_output: str
    duration_seconds: float


class SandboxRunner:
    """Safely executes commands and applies patches inside a repository workspace."""

    def __init__(self, workspace_path: str, timeout: Optional[int] = None):
        self.workspace_path = Path(workspace_path).resolve()
        self.timeout = timeout or settings.sandbox_timeout_seconds
        self.backup_dir = self.workspace_path / ".repoguard_backups"

    def run_tests(self, command: str) -> ExecutionResult:
        """Execute test suite within the workspace and capture results."""
        start_time = time.perf_counter()
        
        # Prepare environment
        env = os.environ.copy()
        env["PYTHONPATH"] = str(self.workspace_path)
        env["PYTHONDONTWRITEBYTECODE"] = "1"

        try:
            process = subprocess.run(
                command,
                cwd=str(self.workspace_path),
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
            )
            duration = time.perf_counter() - start_time
            stdout = process.stdout or ""
            stderr = process.stderr or ""
            combined = (stdout + "\n" + stderr).strip()

            return ExecutionResult(
                exit_code=process.returncode,
                passed=(process.returncode == 0),
                stdout=stdout,
                stderr=stderr,
                combined_output=combined,
                duration_seconds=round(duration, 2),
            )

        except subprocess.TimeoutExpired as e:
            duration = time.perf_counter() - start_time
            timeout_msg = f"Test execution timed out after {self.timeout}s."
            return ExecutionResult(
                exit_code=-1,
                passed=False,
                stdout=e.stdout or "",
                stderr=timeout_msg,
                combined_output=timeout_msg,
                duration_seconds=round(duration, 2),
            )
        except Exception as e:
            duration = time.perf_counter() - start_time
            err_msg = f"Failed to execute test command: {str(e)}"
            return ExecutionResult(
                exit_code=-2,
                passed=False,
                stdout="",
                stderr=err_msg,
                combined_output=err_msg,
                duration_seconds=round(duration, 2),
            )

    def backup_file(self, relative_path: str) -> Path:
        """Create a backup of a file prior to modification."""
        src_path = self.workspace_path / relative_path
        if not src_path.exists():
            return src_path

        self.backup_dir.mkdir(parents=True, exist_ok=True)
        backup_file = self.backup_dir / f"{relative_path}.bak"
        backup_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src_path, backup_file)
        return backup_file

    def restore_backup(self, relative_path: str) -> bool:
        """Restore a backed-up file."""
        backup_file = self.backup_dir / f"{relative_path}.bak"
        target_file = self.workspace_path / relative_path
        if backup_file.exists():
            shutil.copy2(backup_file, target_file)
            return True
        return False

    def apply_patch(self, relative_path: str, new_content: str) -> bool:
        """Apply new code content to the target file safely."""
        target_path = self.workspace_path / relative_path
        self.backup_file(relative_path)
        
        target_path.parent.mkdir(parents=True, exist_ok=True)
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True

    def cleanup_backups(self):
        """Remove temporary backups."""
        if self.backup_dir.exists():
            shutil.rmtree(self.backup_dir, ignore_errors=True)
