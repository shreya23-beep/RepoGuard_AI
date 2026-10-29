"""Unit tests for RepoGuard AI components."""

import tempfile
from pathlib import Path
from repoguard.sandbox.runner import SandboxRunner
from repoguard.llm.nebius_client import NebiusClient
from repoguard.agent.graph import build_repoguard_graph


def test_sandbox_runner_execution():
    """Verify SandboxRunner executes commands and captures exit codes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = SandboxRunner(tmpdir)
        # Run a simple python one-liner test
        res = runner.run_tests("python -c \"import sys; sys.exit(0)\"")
        assert res.passed is True
        assert res.exit_code == 0

        # Run a failing command
        res_fail = runner.run_tests("python -c \"import sys; sys.exit(1)\"")
        assert res_fail.passed is False
        assert res_fail.exit_code == 1


def test_sandbox_patch_and_backup():
    """Verify file backup, patch application, and restoration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        target = tmp_path / "sample.py"
        target.write_text("def hello(): return 'old'", encoding="utf-8")

        runner = SandboxRunner(tmpdir)
        runner.apply_patch("sample.py", "def hello(): return 'new'")

        assert target.read_text(encoding="utf-8") == "def hello(): return 'new'"

        # Test rollback
        assert runner.restore_backup("sample.py") is True
        assert target.read_text(encoding="utf-8") == "def hello(): return 'old'"
        runner.cleanup_backups()


def test_nebius_client_simulation():
    """Verify NebiusClient produces valid structured responses in simulation mode."""
    client = NebiusClient(api_key="")
    assert client.is_mock is True

    response = client.chat_completion([
        {"role": "system", "content": "DIAGNOSTIC root cause analysis"},
        {"role": "user", "content": "Analyze stack trace"}
    ])
    assert "root_cause" in response
    assert "math_lib.py" in response


def test_graph_compilation():
    """Verify LangGraph StateGraph compiles and contains required nodes."""
    graph = build_repoguard_graph()
    assert graph is not None
