"""Command-line interface for RepoGuard AI using Rich."""

import argparse
import logging
import sys
import uuid
from pathlib import Path

# Ensure UTF-8 output on Windows consoles
if sys.platform == "win32":
    try:
        if sys.stdout and hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn

from .agent.graph import build_repoguard_graph
from .agent.state import RepoGuardState
from .config import settings
from .sandbox.runner import SandboxRunner

console = Console(safe_box=True)
logging.basicConfig(level=logging.WARNING)


def run_demo():
    """Run an autonomous self-healing demonstration on the demo repository."""
    mode_str = "[LIVE] Connected to Nebius API" if settings.is_nebius_configured else "[DEMO] Simulated GPU Mode"
    console.print(
        Panel.fit(
            "[bold cyan]RepoGuard AI[/bold cyan] - [bold green]The Self-Healing CI/CD Agent[/bold green]\n"
            "[yellow]Track:[/yellow] Self-Correction (Reflection) Loop & Autonomous Debugging\n"
            f"[yellow]LLM:[/yellow] {settings.nebius_model} via Nebius AI Studio\n"
            f"[yellow]Status:[/yellow] {mode_str}",
            border_style="cyan",
        )
    )

    demo_dir = settings.base_dir / "demo_repo"
    test_cmd = "pytest test_math_lib.py"

    # Step 1: Initial Baseline Test Run
    console.print("\n[bold blue]1. Simulating CI/CD Failure Event...[/bold blue]")
    runner = SandboxRunner(str(demo_dir))
    initial_res = runner.run_tests(test_cmd)

    if not initial_res.passed:
        console.print(f"[red][FAIL] CI Build Failed (Exit code: {initial_res.exit_code})[/red]")
        console.print(
            Panel(
                initial_res.combined_output[-800:],
                title="[bold red]CI Failure Stack Trace[/bold red]",
                border_style="red",
            )
        )
    else:
        console.print("[green]Tests already passing in demo repository![/green]")

    # Step 2: Initialize LangGraph Agent
    console.print("\n[bold blue]2. Initializing RepoGuard AI Self-Correction Agent...[/bold blue]")
    
    run_id = str(uuid.uuid4())[:8]
    initial_state: RepoGuardState = {
        "run_id": run_id,
        "repo_path": str(demo_dir),
        "branch_name": "fix/ci-failure",
        "pr_number": 42,
        "test_command": test_cmd,
        "ci_logs": initial_res.combined_output,
        "current_attempt": 0,
        "max_attempts": settings.max_reflection_attempts,
        "reflection_history": [],
    }

    graph = build_repoguard_graph()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        transient=True,
    ) as progress:
        task = progress.add_task(description="[cyan]Autonomous agent running reflection loop...", total=None)
        
        # Stream updates from the LangGraph execution
        final_state = None
        for step in graph.stream(initial_state):
            for node_name, node_output in step.items():
                progress.stop()
                
                if node_name == "diagnostic":
                    diag = node_output.get("diagnostic", {})
                    attempt = node_output.get("current_attempt", 1)
                    table = Table(title=f"[DIAGNOSIS] State 1: Diagnostic Node (Attempt {attempt})", border_style="magenta")
                    table.add_column("Property", style="bold yellow")
                    table.add_column("Details", style="white")
                    table.add_row("Bug Category", str(diag.get("bug_type")))
                    table.add_row("Target File", str(diag.get("target_file")))
                    table.add_row("Root Cause", str(diag.get("root_cause")))
                    table.add_row("Recommended Action", str(diag.get("recommended_action")))
                    console.print(table)

                elif node_name == "patcher":
                    patch = node_output.get("proposed_patch", {})
                    console.print(f"\n[bold green][PATCH] State 2: Patch Generator Node[/bold green]")
                    console.print(f"[italic]{patch.get('explanation')}[/italic]")
                    if patch.get("fixed_code"):
                        syntax = Syntax(patch.get("fixed_code"), "python", theme="monokai", line_numbers=True)
                        console.print(Panel(syntax, title=f"Generated Code ({patch.get('target_file')})", border_style="green"))

                elif node_name == "verifier":
                    passed = node_output.get("verification_passed", False)
                    status_str = "[bold green][PASS] OK[/bold green]" if passed else "[bold red][FAIL] FAILED[/bold red]"
                    console.print(f"\n[bold yellow][VERIFY] State 3: Sandbox Verification Node[/bold yellow] -> {status_str}")

                elif node_name == "reflection":
                    history = node_output.get("reflection_history", [])
                    latest = history[-1] if history else {}
                    console.print(
                        Panel(
                            f"[bold red]Flaw Identified:[/bold red] {latest.get('reflection_notes')}\n\n"
                            f"[bold cyan]Refined Hypothesis for Next Iteration:[/bold cyan] Looping back to Diagnostic with error feedback.",
                            title="[REFLECT] State 4: Self-Correction (Reflection) Loop",
                            border_style="yellow",
                        )
                    )

                elif node_name == "committer":
                    final_state = node_output
                    report = node_output.get("summary_report", "")
                    console.print(
                        Panel(
                            report,
                            title="[COMMIT] State 5: Committer & Final PR Resolution",
                            border_style="bright_blue",
                        )
                    )
                
                progress.start()

    console.print("\n[bold green]>>> Autonomous CI/CD healing cycle completed successfully![/bold green]\n")


def run_server(host: str = "0.0.0.0", port: int = 8000):
    """Run FastAPI Webhook Server."""
    import uvicorn
    console.print(f"[bold green]Starting RepoGuard AI Webhook Server on {host}:{port}...[/bold green]")
    uvicorn.run("repoguard.integrations.webhook_server:app", host=host, port=port, reload=True)


def run_dashboard():
    """Launch Streamlit Dashboard."""
    import subprocess
    dash_path = settings.base_dir / "repoguard" / "dashboard" / "app.py"
    console.print("[bold green]Launching RepoGuard AI Streamlit Dashboard...[/bold green]")
    subprocess.run(["streamlit", "run", str(dash_path)])


def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="RepoGuard AI: The Self-Healing CI/CD Agent")
    subparsers = parser.add_subparsers(dest="command", help="Available subcommands")

    # Demo
    demo_parser = subparsers.add_parser("demo", help="Run local self-healing demo on demo_repo")

    # Server
    server_parser = subparsers.add_parser("server", help="Start GitHub webhook server")
    server_parser.add_argument("--host", default="0.0.0.0", help="Bind host")
    server_parser.add_argument("--port", type=int, default=8000, help="Bind port")

    # Dashboard
    dash_parser = subparsers.add_parser("dashboard", help="Start Streamlit visualizer")

    args = parser.parse_args()

    if args.command == "demo" or args.command is None:
        run_demo()
    elif args.command == "server":
        run_server(args.host, args.port)
    elif args.command == "dashboard":
        run_dashboard()


if __name__ == "__main__":
    main()
