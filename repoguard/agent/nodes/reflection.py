"""Reflection Node: Self-Correction engine for analyzing why a patch failed."""

import json
import logging
import re
from typing import Any, Dict, List

from ...llm.nebius_client import get_nebius_client
from ..prompts import REFLECTION_SYSTEM_PROMPT
from ..state import RepoGuardState

logger = logging.getLogger("repoguard.reflection")


def _clean_reflection_json(raw_text: str) -> Dict[str, Any]:
    """Extract and parse reflection response."""
    raw_text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
    if match:
        raw_text = match.group(1).strip()
    try:
        return json.loads(raw_text)
    except Exception:
        return {
            "prior_flaw": "Patch failed sandbox verification.",
            "new_hypothesis": "The previous code change introduced a regression or did not satisfy all test assertions.",
            "adjustments_required": "Re-diagnose with strict boundary condition checks."
        }


def reflection_node(state: RepoGuardState) -> Dict[str, Any]:
    """Self-Correction Reflection state handler."""
    current_attempt = state.get("current_attempt", 1)
    diagnostic = state.get("diagnostic", {})
    patch = state.get("proposed_patch", {})
    verification_logs = state.get("verification_logs", "")
    reflection_history = list(state.get("reflection_history", []))

    logger.warning("Executing Reflection Node (Iteration %d Failed). Reflecting on test output...", current_attempt)

    prompt_content = f"""=== FAILED PATCH ATTEMPT (Iteration {current_attempt}) ===
Target: {patch.get('target_file')}
Explanation: {patch.get('explanation')}
Code:
{patch.get('fixed_code')}

=== SANDBOX TEST SUITE FAILURE OUTPUT ===
{verification_logs}

=== ORIGINAL DIAGNOSIS ===
{json.dumps(diagnostic, indent=2)}

Perform reflection analysis on why this patch failed and identify the concrete flaw."""

    client = get_nebius_client()
    response_text = client.chat_completion(
        messages=[
            {"role": "system", "content": REFLECTION_SYSTEM_PROMPT},
            {"role": "user", "content": prompt_content},
        ],
        temperature=0.2,
    )

    reflection_data = _clean_reflection_json(response_text)
    logger.info("Reflection insight: %s", reflection_data.get("new_hypothesis"))

    # Append to trajectory history
    step_record = {
        "attempt": current_attempt,
        "diagnostic": diagnostic,
        "patch": patch,
        "test_passed": False,
        "test_output": verification_logs,
        "reflection_notes": f"Flaw: {reflection_data.get('prior_flaw')} | Hypothesis: {reflection_data.get('new_hypothesis')}",
        "reflection_details": reflection_data,
    }
    reflection_history.append(step_record)

    return {
        "status": "reflecting",
        # Pass the new test logs as the primary CI logs for the next diagnostic turn
        "ci_logs": verification_logs,
        "reflection_history": reflection_history,
    }
