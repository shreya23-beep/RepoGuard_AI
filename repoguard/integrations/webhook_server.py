"""FastAPI Webhook Server for receiving GitHub CI events and dispatching RepoGuard agent."""

import logging
import uuid
from typing import Any, Dict, Optional
from fastapi import FastAPI, BackgroundTasks, Header, HTTPException, Request
from pydantic import BaseModel

from ..agent.graph import build_repoguard_graph
from ..agent.state import RepoGuardState
from ..config import settings

logger = logging.getLogger("repoguard.server")

app = FastAPI(
    title="RepoGuard AI - Webhook Server",
    description="Autonomous CI/CD Healing Agent powered by Nebius AI Studio & LangGraph",
    version="1.0.0",
)

# In-memory store for recent execution runs
active_runs: Dict[str, Dict[str, Any]] = {}


class TriggerHealRequest(BaseModel):
    repo_path: Optional[str] = None
    repo_url: Optional[str] = None
    branch_name: Optional[str] = "main"
    pr_number: Optional[int] = None
    test_command: str = "pytest"
    ci_logs: Optional[str] = None


def execute_healing_pipeline(run_id: str, initial_state: RepoGuardState):
    """Background task executing the LangGraph healing state machine."""
    try:
        active_runs[run_id]["status"] = "in_progress"
        graph = build_repoguard_graph()
        
        # Stream or invoke workflow
        final_state = graph.invoke(initial_state)
        
        active_runs[run_id]["status"] = final_state.get("status", "completed")
        active_runs[run_id]["final_state"] = final_state
        logger.info("Healing workflow %s completed with status: %s", run_id, final_state.get("status"))
    except Exception as e:
        logger.exception("Error executing healing pipeline for run %s: %s", run_id, e)
        active_runs[run_id]["status"] = "error"
        active_runs[run_id]["error"] = str(e)


@app.get("/health")
def health_check():
    """Health status and configuration overview."""
    return {
        "status": "online",
        "service": "RepoGuard AI",
        "model": settings.nebius_model,
        "nebius_configured": settings.is_nebius_configured,
        "sandbox_mode": settings.sandbox_mode,
    }


@app.post("/webhook")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_github_event: Optional[str] = Header(None),
):
    """Ingest GitHub webhook events (workflow_run, check_run, push)."""
    payload = await request.json()
    logger.info("Received GitHub Webhook Event: %s", x_github_event)

    # Filter for workflow_run failure
    if x_github_event == "workflow_run":
        action = payload.get("action")
        workflow_run = payload.get("workflow_run", {})
        conclusion = workflow_run.get("conclusion")

        if action == "completed" and conclusion == "failure":
            head_branch = workflow_run.get("head_branch", "main")
            repo = payload.get("repository", {})
            repo_url = repo.get("clone_url")
            pull_requests = workflow_run.get("pull_requests", [])
            pr_num = pull_requests[0].get("number") if pull_requests else None

            run_id = str(uuid.uuid4())
            initial_state: RepoGuardState = {
                "run_id": run_id,
                "repo_path": str(settings.base_dir / "demo_repo"),
                "branch_name": head_branch,
                "pr_number": pr_num,
                "test_command": "pytest",
                "ci_logs": f"Workflow '{workflow_run.get('name')}' failed on branch '{head_branch}'.",
                "current_attempt": 0,
                "max_attempts": settings.max_reflection_attempts,
                "reflection_history": [],
            }

            active_runs[run_id] = {
                "run_id": run_id,
                "status": "queued",
                "event": "workflow_run.failure",
            }

            background_tasks.add_task(execute_healing_pipeline, run_id, initial_state)
            return {"status": "accepted", "run_id": run_id, "message": "RepoGuard AI self-healing initiated"}

    return {"status": "ignored", "reason": f"Event '{x_github_event}' did not trigger healing."}


@app.post("/api/heal")
def manual_trigger(req: TriggerHealRequest, background_tasks: BackgroundTasks):
    """Direct API endpoint to trigger RepoGuard AI healing on any repo."""
    run_id = str(uuid.uuid4())
    repo_path = req.repo_path or str(settings.base_dir / "demo_repo")

    initial_state: RepoGuardState = {
        "run_id": run_id,
        "repo_path": repo_path,
        "branch_name": req.branch_name or "main",
        "pr_number": req.pr_number,
        "test_command": req.test_command,
        "ci_logs": req.ci_logs or "Manual trigger: initial test failure detected.",
        "current_attempt": 0,
        "max_attempts": settings.max_reflection_attempts,
        "reflection_history": [],
    }

    active_runs[run_id] = {
        "run_id": run_id,
        "status": "queued",
        "repo_path": repo_path,
    }

    background_tasks.add_task(execute_healing_pipeline, run_id, initial_state)
    return {"status": "accepted", "run_id": run_id, "message": "RepoGuard AI healing dispatched."}


@app.get("/api/status/{run_id}")
def get_run_status(run_id: str):
    """Check status of an active or completed healing run."""
    if run_id not in active_runs:
        raise HTTPException(status_code=404, detail="Run ID not found")
    return active_runs[run_id]
