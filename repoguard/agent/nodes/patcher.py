"""Patcher Node: Generates and applies targeted code patches using Nebius Nemotron-70B."""

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict

from ...llm.nebius_client import get_nebius_client
from ...sandbox.runner import SandboxRunner
from ..prompts import PATCH_SYSTEM_PROMPT, PATCH_USER_TEMPLATE
from ..state import RepoGuardState

logger = logging.getLogger("repoguard.patcher")


def _clean_patch_json(raw_text: str, default_file: str) -> Dict[str, Any]:
    """Clean and extract patch JSON from LLM response."""
    raw_text = raw_text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", raw_text)
    if match:
        raw_text = match.group(1).strip()
    try:
        data = json.loads(raw_text)
        if "target_file" not in data or not data["target_file"]:
            data["target_file"] = default_file
        return data
    except Exception:
        return {
            "explanation": "Extracted code patch",
            "target_file": default_file,
            "fixed_code": raw_text
        }


def patcher_node(state: RepoGuardState) -> Dict[str, Any]:
    """Patch generation and application state handler."""
    repo_path = Path(state.get("repo_path", ".")).resolve()
    diagnostic = state.get("diagnostic", {})
    target_file = diagnostic.get("target_file", "math_lib.py")
    reflection_history = state.get("reflection_history", [])

    logger.info("Executing Patcher Node for target: %s", target_file)

    # Read target file content
    file_path = repo_path / target_file
    if file_path.exists():
        file_content = file_path.read_text(encoding="utf-8")
    else:
        file_content = "# Target file not found, creating new file."

    # Format reflection context
    if reflection_history:
        notes = [f"Attempt {s.get('attempt')}: {s.get('reflection_notes')}" for s in reflection_history]
        reflection_context = "\n".join(notes)
    else:
        reflection_context = "No previous patches for this session."

    user_prompt = PATCH_USER_TEMPLATE.format(
        diagnostic_json=json.dumps(diagnostic, indent=2),
        target_file=target_file,
        file_content=file_content,
        reflection_context=reflection_context,
    )

    client = get_nebius_client()
    response_text = client.chat_completion(
        messages=[
            {"role": "system", "content": PATCH_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.2,
    )

    patch_data = _clean_patch_json(response_text, default_file=target_file)
    fixed_code = patch_data.get("fixed_code", "")

    # Apply the patch in the sandbox
    runner = SandboxRunner(str(repo_path))
    if fixed_code:
        runner.apply_patch(target_file, fixed_code)
        logger.info("Applied patch to %s successfully.", target_file)

    return {
        "status": "patching",
        "proposed_patch": patch_data,
    }
