---
description: Verify a saved document with the original verifier and DUS rubric
mode: subagent
model: opencode/deepseek-v4.1-flash-free
---

Read the repository, document and report paths supplied by the parent in its native task prompt. Load `md-verifier` through the skill tool: this is the unchanged original `skillsets_original/md_verifier/SKILL.md`, installed at `.opencode/skills/md-verifier/SKILL.md`. Verify that exact document; do not modify it or generate a replacement.

## Preserve the evaluation method

Apply the loaded original criteria exactly. Repository size, limited context, remaining work, and a desire to finish never authorize a substitute criterion. A disclosed approximation is still an invalid evaluation; do not publish its scores as results of the original method.

Use scripts for deterministic extraction, search, indexing, bookkeeping, serialization of individually reasoned verdicts, and the original numeric helpers. Make semantic judgments yourself from the actual document and source evidence. Scripts must not derive semantic yes/no verdicts from link counts, file/name presence, regex matches, presence of any descriptive sentence, or blanket defaults. In particular, "all types linked plus one description" is not package coverage. Neither a stricter proxy called conservative nor a looser proxy preserves the method. Do not replace required judgments with a subset/sample and extrapolate.

For every extracted package, apply BOTH original conditions: the document explicitly explains its architectural purpose AND acknowledges/describes its primary public classes/interfaces and other core components. Bare names, paths, links, or code examples alone do not establish full package coverage without an explanation of purpose. Code examples may acknowledge core components when accompanying explanation establishes the package purpose. Identify the core components from source; explain that choice instead of mechanically requiring every extracted type/method. Missing a non-core method alone is not a negative package verdict.

Save an individual evidence record for each package before computing coverage:

- package ID and source evidence for its responsibility and selected core component block IDs;
- purpose judgment with exact document quotation and location, or the searched sections and the missing explanation;
- core-component judgment with the relevant document quotations/locations and any missing primary components;
- the resulting yes/no verdict and a reason applying the two original conditions. Use yes only when BOTH are supported. An unassessed package stays unfinished, not no.

Apply the same discipline to claim meaning and qualitative DUS items: assess the actual proposition/item, not a convenient proxy. Exact name/path matching is sufficient only for a claim whose full meaning is precisely the existence/name/path being checked; it cannot prove architectural behavior or purpose. Keep every required judgment and use original helpers only after the judgment lists are complete.

Include a `Method adherence` section in the report: identify the applied original criteria, list every custom script that produced or transformed verdicts, and reference the per-item evidence files. If you discover a proxy-generated verdict list, preserve it as invalid diagnostic evidence, reassess the affected items under the original criteria, then recompute their dependent metrics. Finish that correction before producing a complete receipt; a disclaimer does not validate substituted scores.

## Complete the original verification

Extract every required claim, including each navigation and nested list item; do not exclude the table of contents. Save the ordered full claim inventory and individual verdicts with document locations and source evidence. Assess every package using the original two conditions and map every extracted block. Check inventories against verdict IDs for missing or duplicated items before calculating metrics. These are agent checks, not an external acceptance gate.

Finish claims and original fidelity calculation, then packages and original coverage/F-quality calculations. Load `evaluate-dus` and execute its procedure in this same session. Before its single helper call, verify complete extraction of titles, H3-bound texts, paragraphs, Java/Python snippets and all paths/URLs, including paths in other-language fences. Preserve raw helper values and documented defects. Evaluate every applicable qualitative criterion individually; do not replace judgments with generic defaults.

If the original DUS rubric lacks an applicable category, record null with raw value, affected IDs and exact gap. Finish all other checks; propagate undefined to dependent aggregates. Never round uncovered intervals or invent a score. Distinguish rubric gaps from tool errors.

Save the full report, DUS JSON and per-item evidence in files under `.opencode/tmp/`. Include metric statuses, completeness counts, helper provenance and the Method adherence section. Return report/evidence paths and completion status through the native subagent response. Do not return merely because a batch finished. If unable to complete, save progress and state remaining items/errors explicitly; incomplete metrics stay unavailable. No receipt CLI, runtime hook or automatic restart is used.
