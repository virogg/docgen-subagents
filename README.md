# Documentation generation with OpenCode subagents

`md-doc-gen` runs the original documentation pipeline. It calls `code-summarizer` to generate a draft and `md-verifier` to verify it and evaluate DUS. OpenCode starts and waits for the child sessions. They exchange file paths in their task prompts and replies.

The original skills and metric helpers are bundled in `skillsets_original/`. The three files in `agents/` configure their roles. When the DUS rubric lacks an applicable category, the verifier reports it as undefined and finishes the other checks.

## Install

Use OpenCode 2.2.6 and a Python 3.11+ environment with the original helper dependencies. Run from this repository, replacing `/path/to/repo` with the target directory and selecting a tool-capable model available in your OpenCode setup. The installer requires that the target installation paths are free.

```sh
python -m pip install -r skillsets_original/doc_gen/requirements.txt requests
python install.py /path/to/repo /path/to/repo/.opencode --model openai/gpt-6.1-sol
```

Run OpenCode from the target repository with the same Python environment active. The profiles call the installed Python functions through the shell.

```sh
cd /path/to/repo
opencode run --agent md-doc-gen "Generate documentation for this repository."
```

The profiles use ordinary output files under `.opencode/` and ask each child to report incomplete work explicitly. OpenCode manages the calls between agents.
