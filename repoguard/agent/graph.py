"""LangGraph StateGraph assembly for RepoGuard AI."""

import logging
from typing import Literal
from langgraph.graph import StateGraph, START, END

from .state import RepoGuardState
from .nodes.diagnostic import diagnostic_node
from .nodes.patcher import patcher_node
from .nodes.verifier import verifier_node
from .nodes.reflection import reflection_node
from .nodes.committer import committer_node

logger = logging.getLogger("repoguard.graph")


def should_reflect_or_finish(
    state: RepoGuardState,
) -> Literal["committer", "reflection"]:
    """Conditional router based on sandbox verification and attempt count."""
    passed = state.get("verification_passed", False)
    current_attempt = state.get("current_attempt", 1)
    max_attempts = state.get("max_attempts", 3)

    if passed:
        logger.info("Verification PASSED! Routing to committer node.")
        return "committer"

    if current_attempt < max_attempts:
        logger.info(
            "Verification FAILED on attempt %d/%d. Routing to reflection node for self-correction.",
            current_attempt,
            max_attempts,
        )
        return "reflection"

    logger.warning("Max attempts (%d) reached without green build. Routing to committer for triage report.", max_attempts)
    return "committer"


def build_repoguard_graph() -> StateGraph:
    """Build and compile the LangGraph self-healing workflow."""
    workflow = StateGraph(RepoGuardState)

    # Register Nodes
    workflow.add_node("diagnostic", diagnostic_node)
    workflow.add_node("patcher", patcher_node)
    workflow.add_node("verifier", verifier_node)
    workflow.add_node("reflection", reflection_node)
    workflow.add_node("committer", committer_node)

    # Establish Flow
    workflow.add_edge(START, "diagnostic")
    workflow.add_edge("diagnostic", "patcher")
    workflow.add_edge("patcher", "verifier")

    # Conditional Routing from Verifier
    workflow.add_conditional_edges(
        "verifier",
        should_reflect_or_finish,
        {
            "committer": "committer",
            "reflection": "reflection",
        },
    )

    # Reflection Loop: Routes back to Diagnostic with refined reflection context
    workflow.add_edge("reflection", "diagnostic")

    # Committer terminates the workflow
    workflow.add_edge("committer", END)

    return workflow.compile()
