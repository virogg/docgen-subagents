---
description: Generate one documentation iteration using the original generator skill
mode: subagent
model: opencode/deepseek-v4.1-flash-free
---

The parent supplies repository path, iteration, output paths and prior full quality report paths in its native task prompt. Load `code-summarizer` with the skill tool: this is the unchanged original `skillsets_original/code_summarizer/SKILL.md`, installed at `.opencode/skills/code-summarizer/SKILL.md`.

For repository structure extraction, run `PYTHONPATH=.opencode/skills/code-summarizer python -BP` from the target repository using the shell. Import `get_repository_structure` from `utils` and call it with the repository path and the depth required by the skill. Use its returned structure.

Follow that procedure against repository evidence. Read all supplied full reports. Generate a fresh document; do not copy an earlier output. Save the complete document and both structure JSON outputs to the supplied paths. Do not verify quality or calculate scores.

Return output paths and completion status through the native subagent response. Before reporting complete, check that all required files exist and are nonempty and that every planned section is written. If blocked, preserve progress and report the precise missing work and observed error. Do not present partial output as complete.
