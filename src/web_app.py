"""Simple Streamlit web UI for the Repo Explainer Agent.

Overview:
 - Page setup: Streamlit metadata and titles
 - Inputs: repo path + freeform question
 - Execution: build RepoTools + RepoExplainerAgent, run deterministic answer
 - Display: left column shows answer + cited evidence; right shows tool calls,
   inspected files, and suggested next steps (if more info is needed)
"""

import streamlit as st
from pathlib import Path
import io
import re
import tempfile
import urllib.request
import zipfile

from agent.tools import RepoTools
from agent.orchestrator import RepoExplainerAgent


# Page setup
st.set_page_config(page_title="Repo Explainer Agent", layout="wide")
st.title("Repo Explainer Agent")
st.markdown(
    '<div style="color:#0B3D91; font-size:1.15em; font-weight:600; margin-bottom:12px;">'
    'Deterministic tool-using agent: searches + reads + cites evidence (no guessing).'
    "</div>",
    unsafe_allow_html=True,
)


# Two-column layout: inputs on the left, results on the right
left_col, right_col = st.columns([1, 1])

# Inputs (left column)
with left_col:
    repo_path = st.text_input(
        "Repo path",
        value="",
        placeholder="e.g. /path/to/repo or https://github.com/owner/repo",
    )
    if len((repo_path or "").strip()) == 0:
        st.markdown(
            '<div style="color:#c62828; font-weight:600; margin-top:4px;">'
            "Please provide a repo path..."
            "</div>",
            unsafe_allow_html=True,
        )

# Curated, general-purpose questions that work for many repos
COMMON_QUESTIONS = [
    "How do I run this project locally?",
    "Where is the main entry point?",
    "How are tests run and configured?",
    "How is authentication handled?",
    "Where is configuration loaded and managed?",
    "How does logging work?",
    "Where are the API routes/endpoints defined?",
    "How are dependencies and packaging set up?",
    "What background jobs or workers exist?",
    "How is database access or persistence implemented?",
]

# Selection control to quickly populate the question field
with left_col:
    preset = st.selectbox(
        "Common questions",
        ["Custom (type your own)"] + COMMON_QUESTIONS,
        index=0,
    )

# Keep the text area in sync with the selected preset (but allow edits)
if "question_text" not in st.session_state:
    st.session_state["question_text"] = "Where is authentication handled?"
if preset != "Custom (type your own)" and st.session_state.get("last_applied_preset") != preset:
    st.session_state["question_text"] = preset
    st.session_state["last_applied_preset"] = preset

with left_col:
    question = st.text_area("Ask a question", value=st.session_state["question_text"], key="question_text")
    # Disable Ask until a repo path/URL is provided
    ask_disabled = len((repo_path or "").strip()) == 0
    ask_clicked = st.button("Ask", disabled=ask_disabled)


# Helpers
def fetch_github_zip(url: str) -> Path:
    """Download a public GitHub repo as a ZIP and return extracted root path.

    Chunk responsibilities:
      - Parse common GitHub URL forms, infer branch (default: main)
      - Download the ZIP via urllib (no extra deps)
      - Extract to a temporary directory and return the repo root
    """
    m = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/(?:tree|blob)/([^/]+))?/?$", url.strip())
    if not m:
        raise ValueError("Unsupported GitHub URL. Example: https://github.com/owner/repo or /tree/branch")
    owner, repo, branch_hint = m.group(1), m.group(2), m.group(3)
    repo = repo.removesuffix(".git")
    tmpdir = Path(tempfile.mkdtemp(prefix="repo-explainer-"))

    # Try a small set of common branches to avoid 404s when default is not 'main'
    candidates = [branch_hint] if branch_hint else []
    candidates += ["main", "master", "develop", "dev"]

    last_error: Exception | None = None
    extracted = False
    for branch in [b for b in candidates if b]:
        zip_url = f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip"
        try:
            data = urllib.request.urlopen(zip_url, timeout=30).read()
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                zf.extractall(tmpdir)
            extracted = True
            break
        except Exception as e:  # noqa: BLE001 - we surface specific error below
            last_error = e
            continue

    if not extracted:
        raise last_error or RuntimeError("Failed to download repository ZIP")

    # Use the single top-level directory if present
    subdirs = [p for p in tmpdir.iterdir() if p.is_dir()]
    return subdirs[0] if len(subdirs) == 1 else tmpdir


# Execution + Display (right column shows results)
if ask_clicked:
    # Accept either a local path or a public GitHub URL
    repo_input = repo_path.strip()
    if not repo_input:
        right_col.warning("Please enter a repo path or public GitHub URL, then click Ask.")
        st.stop()
    try:
        if repo_input.startswith("http://") or repo_input.startswith("https://"):
            with st.spinner("Downloading GitHub repository..."):
                extracted = fetch_github_zip(repo_input)
                resolved_repo = extracted
                right_col.caption(f"Using downloaded copy at: {resolved_repo}")
        else:
            resolved_repo = Path(repo_input).expanduser().resolve()

        # Create tools/agent for the resolved repository root
        tools = RepoTools(resolved_repo)
    except Exception as e:
        right_col.error(f"Failed to prepare repository: {e}")
        st.stop()
    agent = RepoExplainerAgent(tools)

    result = agent.answer(question)

    # Right column: main answer and evidence citations
    with right_col:
        st.subheader("Answer")
        st.write(result.answer)

        st.subheader("Evidence")
        if result.evidence:
            for e in result.evidence:
                st.markdown(f"**{e.path}:{e.line_start}-{e.line_end}**")
                st.code(e.text)
        else:
            st.info("No evidence collected yet.")

        # Tool calls, inspected files, and suggested next steps
        st.subheader("Tool Calls")
        for tc in result.tool_calls:
            st.markdown(f"- **{tc.name}** `{tc.args}` → {tc.result_preview}")

        st.subheader("Inspected Files")
        if result.inspected_files:
            st.write(result.inspected_files)
        else:
            st.write("None")

        if result.needs_more_info:
            st.subheader("Suggested next steps")
            for s in result.suggested_next_steps:
                st.write(f"- {s}")


