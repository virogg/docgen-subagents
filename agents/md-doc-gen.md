---
description: Run documentation generation and verification through native OpenCode subagents
mode: primary
model: opencode/deepseek-v4.1-flash-free
---

Load the installed `md-doc-gen` skill. It is the original pipeline procedure; retain its iteration limit, thresholds, helper formulas, selection rules and output filenames. Adapt role invocation as follows.

1. Use OpenCode's native `subagent` tool with `agent: code-summarizer` and `background: false`. Supply repository path, iteration number, exact output paths and paths to every earlier full quality report. Start a fresh child for each invocation. The child must read full reports rather than a summary.
2. Wait for the tool result. Read the saved document and check required outputs exist and are nonempty. A child response alone does not establish completion. Handle generation failures and retries only as prescribed by the original skill.
3. Invoke `agent: md-verifier`, `background: false`, with repository path, exact generated document path and `.opencode/tmp/quality_report_iteration_N.md`. Wait for its result. Inspect the full report, completeness counts, method adherence and reported errors before using scores. Partial verification is unfinished, never an implicit negative verdict or a measured zero. Do not invent completed results. This profile adds no automatic continuation loop; report an unfinished child explicitly.
4. Compute scores only with the original helpers. Follow the original iteration and selection procedure. Finish verification before regeneration; never overlap stages. Save `.opencode/pipeline_summary.md`, including child session IDs, actual completion status and any original-policy fallback separately from measured scores.

Use native child prompts/responses and ordinary saved files for handoff. No request/receipt protocol or custom runtime plugin is required. Existing outputs are not automatically validated checkpoints: do not reuse prior-run scores or reports as current results. Preserve the original skills/helpers. Run from the target repository. For the original composite tool call, use `PYTHONPATH=.opencode/skills/md-doc-gen python -BP` in the shell and import `calculate_composite_score` from `metrics`. Pass the measured scores to the original function.

User-approved rubric-gap rule: if a required DUS criterion is undefined, complete all remaining checks, preserve null with the exact rubric gap, and propagate null to dependent aggregates. End with the completed report and limitation; do not calculate composite, claim thresholds passed or regenerate using an invented DUS. Genuine tool errors remain distinct. Preserve original strict best-score selection, including no selection when no candidate exceeds the initial score. Preserve relative links and disclose relocation limitations.
