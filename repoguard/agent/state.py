"""State definitions for LangGraph-based RepoGuard AI agent."""

from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict
from pydantic import BaseModel, Field


class ReflectionStep(BaseModel):
    """Record of a single self-correction / reflection iteration."""
    attempt: int
    diagnostic: Dict[str, Any]
    patch: Dict[str, Any]
    test_passed: bool
    test_output: str
    reflection_notes: str = ""


class RepoGuardState(TypedDict, total=False):
    """State graph schema tracked across the entire CI/CD healing cycle."""
    run_id: str
    repo_path: str
    branch_name: str
    pr_number: Optional[int]
    test_command: str
    ci_logs: str
    
    # State tracking
    current_attempt: int
    max_attempts: int
    status: str  # "starting", "diagnosing", "patching", "verifying", "reflecting", "healed", "failed"
    
    # Node outputs
    diagnostic: Optional[Dict[str, Any]]
    proposed_patch: Optional[Dict[str, Any]]
    verification_passed: bool
    verification_logs: str
    
    # Reflection history: stores all prior attempts for self-correction context
    reflection_history: List[Dict[str, Any]]
    
    # Final resolution
    commit_sha: Optional[str]
    summary_report: Optional[str]
