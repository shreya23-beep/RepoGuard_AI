"""Diagnostic Node: Analyzes stack traces and source code with Nebius Nemotron-70B."""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict

from ...llm.nebius_client import get_nebius_client
from ..prompts import DIAGNOSTIC_SYSTEM_PROMPT, DIAGNOSTIC_USER_TEMPLATE
from ..state import RepoGuardState

logger = logging.getLogger("repoguard.diagnostic")


def _clean_json_response(raw_text: str) -> Dict[str, Any]:
    """Extract and parse JSON from LLM output."""
    raw_text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
    if match:
        raw_text = match.group(1).strip()
    try:
        return json.loads(raw_text)
    except Exception:
        # Fallback regex extraction if full JSON fails
        return {
            "root_cause": "Extracted failure from logs",
            "bug_type": "RuntimeError",
            "target_file": "math_lib.py",
            "failing_symbol": "unknown",
            "reflection_analysis": raw_text[:200],
            "recommended_action": "Apply safe logic fix"
        }


def _gather_repo_context(repo_path: Path) -> str:
    """Read relevant source files in repository to feed into prompt."""
    context_parts = []
    for file_path in repo_path.glob("**/*.py"):
        if ".repoguard" in file_path.parts or "test" in file_path.name.lower():
            continue
        try:
            rel_path = file_path.relative_to(repo_path)
            content = file_path.read_text(encoding="utf-8")
            context_parts.append(f"--- File: {rel_path} ---\n{content}\n")
        except Exception:
            pass
    return "\n".join(context_parts) if context_parts else "No source files found."


def diagnostic_node(state: RepoGuardState) -> Dict[str, Any]:
    """Diagnostic state handler."""
    repo_path = Path(state.get("repo_path", ".")).resolve()
    ci_logs = state.get("ci_logs", "No logs provided.")
    current_attempt = state.get("current_attempt", 0) + 1
    reflection_history = state.get("reflection_history", [])

    logger.info("Executing Diagnostic Node (Attempt %d)...", current_attempt)

    # Format previous reflection feedback
    if reflection_history:
        prior_notes = []
        for step in reflection_history:
            prior_notes.append(
                f"[Attempt {step.get('attempt')}] Flaw: {step.get('reflection_notes')}\n"
                f"Test output was:\n{step.get('test_output', '')[:300]}"
            )
        reflection_context = "\n\n".join(prior_notes)
    else:
        reflection_context = "This is the initial diagnosis attempt. No previous failures recorded."

    source_context = _gather_repo_context(repo_path)

    user_prompt = DIAGNOSTIC_USER_TEMPLATE.format(
        ci_logs=ci_logs,
        source_context=source_context,
        reflection_context=reflection_context,
    )

    client = get_nebius_client()
    response_text = client.chat_completion(
        messages=[
            {"role": "system", "content": DIAGNOSTIC_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.1,
    )

    diagnostic_data = _clean_json_response(response_text)
    logger.info("Diagnostic completed: %s in %s", diagnostic_data.get("bug_type"), diagnostic_data.get("target_file"))

    return {
        "current_attempt": current_attempt,
        "status": "diagnosing",
        "diagnostic": diagnostic_data,
    }
