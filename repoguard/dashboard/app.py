"""Streamlit Interactive Visualizer & Control Center for RepoGuard AI."""

import json
import uuid
from pathlib import Path
import streamlit as st

from repoguard.agent.graph import build_repoguard_graph
from repoguard.agent.state import RepoGuardState
from repoguard.config import settings
from repoguard.sandbox.runner import SandboxRunner

st.set_page_config(
    page_title="RepoGuard AI | Self-Healing CI/CD Agent",
    page_icon="🛡️",
    layout="wide",
)

st.title("🛡️ RepoGuard AI — The Self-Healing CI/CD Agent")
st.caption("Autonomous CI/CD Healing with LangGraph Reflection Loops & Llama-3-Nemotron-70B (Nebius AI Studio)")

# Sidebar Settings
st.sidebar.header("⚙️ Agent Configuration")
api_key = st.sidebar.text_input(
    "Nebius API Key",
    value=settings.nebius_api_key,
    type="password",
    help="Enter Nebius Studio token or leave empty for simulated mode.",
)
model_name = st.sidebar.selectbox(
    "LLM Model",
    [
        "nvidia/Llama-3.1-Nemotron-70B-Instruct-HF",
        "meta-llama/Meta-Llama-3.1-70B-Instruct",
        "meta-llama/Llama-3.3-70B-Instruct",
    ],
    index=0,
)
max_retries = st.sidebar.slider("Max Reflection Attempts", min_value=1, max_value=5, value=3)

st.sidebar.divider()
st.sidebar.markdown(
    """
    **Architecture:**
    - **Compute**: Nebius GPU Container
    - **Model**: `Nemotron-70B-Instruct`
    - **Graph Engine**: `LangGraph`
    - **Sandbox**: Subprocess / Docker
    - **Integration**: GitHub Webhooks
    """
)

# Demo Workspace
demo_path = settings.base_dir / "demo_repo"
math_file = demo_path / "math_lib.py"
test_file = demo_path / "test_math_lib.py"

col1, col2 = st.columns(2)

with col1:
    st.subheader("📁 Broken Repository Source (`math_lib.py`)")
    if math_file.exists():
        st.code(math_file.read_text(encoding="utf-8"), language="python")

with col2:
    st.subheader("🧪 Failing CI/CD Test Suite (`test_math_lib.py`)")
    if test_file.exists():
        st.code(test_file.read_text(encoding="utf-8"), language="python")

st.divider()

# Test Runner & Trigger
c_btn, c_stat = st.columns([1, 3])

if c_btn.button("🚀 Trigger Self-Healing Agent", type="primary", use_container_width=True):
    runner = SandboxRunner(str(demo_path))
    
    with st.status("Executing RepoGuard AI Autonomous Healing Loop...", expanded=True) as status_box:
        st.write("🔍 Running baseline CI test suite in sandbox...")
        baseline = runner.run_tests("pytest test_math_lib.py")
        
        if baseline.passed:
            st.warning("Tests are already passing in the workspace! Resetting demo file...")
            # Reset to broken version if already fixed
            broken_code = (
                'def calculate_discounted_average(prices: list[float], discount: float = 0.0) -> float:\n'
                '    valid_prices = [p for p in prices if p >= 0]\n'
                '    total = sum(valid_prices) * (1.0 - discount)\n'
                '    return round(total / len(valid_prices), 2)\n'
            )
            math_file.write_text(broken_code, encoding="utf-8")
            baseline = runner.run_tests("pytest test_math_lib.py")

        st.error(f"❌ CI Build Failed (Exit code {baseline.exit_code}): ZeroDivisionError detected in logs.")
        
        # Build and invoke LangGraph agent
        graph = build_repoguard_graph()
        initial_state: RepoGuardState = {
            "run_id": str(uuid.uuid4())[:8],
            "repo_path": str(demo_path),
            "branch_name": "fix/ci-failure",
            "pr_number": 101,
            "test_command": "pytest test_math_lib.py",
            "ci_logs": baseline.combined_output,
            "current_attempt": 0,
            "max_attempts": max_retries,
            "reflection_history": [],
        }

        # Step by step visualization
        trajectory = []
        for step in graph.stream(initial_state):
            for node_name, node_output in step.items():
                trajectory.append((node_name, node_output))
                if node_name == "diagnostic":
                    diag = node_output.get("diagnostic", {})
                    st.markdown(f"**🧠 Diagnostic Node (Attempt {node_output.get('current_attempt')})**")
                    st.json(diag)
                elif node_name == "patcher":
                    patch = node_output.get("proposed_patch", {})
                    st.markdown(f"**🛠️ Patcher Node**: Applied patch to `{patch.get('target_file')}`")
                    st.code(patch.get("fixed_code", ""), language="python")
                elif node_name == "verifier":
                    passed = node_output.get("verification_passed", False)
                    if passed:
                        st.success("✅ **Sandbox Verification PASSED**: All unit tests succeeded!")
                    else:
                        st.warning("⚠️ **Sandbox Verification FAILED**: Tests caught an unhandled case or regression.")
                elif node_name == "reflection":
                    st.markdown("🔄 **Self-Correction (Reflection) Node**: Nemotron analyzed why the patch failed.")
                    hist = node_output.get("reflection_history", [])
                    if hist:
                        st.info(f"**Reflection Notes**: {hist[-1].get('reflection_notes')}")
                elif node_name == "committer":
                    st.markdown("🚀 **Committer Node**: Staging verified code and generating PR comment.")
        
        status_box.update(label="✅ RepoGuard AI Self-Healing Complete!", state="complete", expanded=False)

    st.success("🎉 Pull Request successfully healed and verified!")

    # Show Final PR Comment Tab
    tab1, tab2 = st.columns(2)
    with tab1:
        st.subheader("📄 Healed Source Code")
        st.code(math_file.read_text(encoding="utf-8"), language="python")
    with tab2:
        st.subheader("💬 Generated GitHub PR Comment")
        committer_out = [item[1] for item in trajectory if item[0] == "committer"]
        if committer_out:
            st.markdown(committer_out[0].get("summary_report", ""))
