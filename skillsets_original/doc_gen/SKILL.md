---
name: md-doc-gen
description: "Create comprehensive code repository documentation with iterative quality improvement. Use when the user asks to summarize code or generate documentation for the project by path <path/to/repo> with the best quality."
license: MIT
compatibility: opencode
---

# Documentation Pipeline Orchestrator

## Overview

This skill orchestrates the complete documentation generation pipeline by coordinating two specialized skills:

| Skill | Name | Responsibility |
|-------|------|----------------|
| Generator | `code-summarizer` | Produces documentation (Phases 1-4) |
| Verifier | `md-verifier` | Evaluates documentation quality (3 standard metrics + internal DUS metric) |

This orchestrator manages the iteration loop, tracks the best document across multiple dimensions, and makes final selection decisions.

---

## Configuration

| Parameter | Value |
|-----------|-------|
| **Maximum Iterations** | 5 |
| **Standard Quality Threshold** | 0.65 |
| **DUS Quality Threshold** | 0.7 |

---

## State Variables

Initialize before execution:

```
iteration_counter = 0
best_document_path = null
best_composite_score = 0.0
current_document_path = null
quality_reports = []
all_scores = []
```

---

## Orchestrator Algorithm

### Phase 0: Environment Setup

```
STEP 1: CREATE directory {{repository_name}}/.opencode/ (if not exists)
STEP 2: INITIALIZE all state variables
```

### Phase 1: First Generation

```
STEP 3: INVOKE code-summarizer
    - INPUT: repository_name = {{repository_name}}, quality_reports = null
    - OUTPUT: generated document

    [SOLE_METHOD] This INVOKE is the ONLY valid way to produce documentation 
    content. Do NOT write documentation manually or generate it via a script.

STEP 4: SET current_document_path = "{{repository_name}}/.opencode/tmp/generated_document_iteration_1.md"

STEP 5: SAVE generated document to current_document_path

    [VALIDATION] After saving, verify the file exists and is non-empty before 
    proceeding. If empty or missing, treat as "Generator produces empty 
    document" error (see Error Handling table).

STEP 6: SET iteration_counter = 1
```

### Phase 2: Verification and Iteration Loop

```
STEP 7: WHILE iteration_counter <= 5:

    STEP 7.1: INVOKE md-verifier
        - INPUT: document_path = current_document_path, repository_name = {{repository_name}}
        - OUTPUT: quality_report

        [SERIALIZATION] This step MUST NOT start until the document at 
        current_document_path is fully written to disk (Step 5 or Step 7.12). 
        Do NOT invoke verifier in parallel with generator.

        [SOLE_METHOD] This INVOKE is the ONLY valid way to obtain scores. 
        See [FORBIDDEN] below.

        [FORBIDDEN] Do NOT calculate, estimate, fabricate, or approximate 
        any scores (MD_to_Code_Score, Code_to_MD_Score, F_Quality_Score, 
        final_dus_score) yourself. Do NOT write a Python script to compute 
        them. Do NOT reuse scores from previous iterations. Every score 
        MUST come from a fresh md-verifier invocation on the current 
        iteration's document.

    STEP 7.2: EXTRACT from quality_report:
        - MD_to_Code_Score
        - Code_to_MD_Score
        - F_Quality_Score
        - final_dus_score (extracted from internal DUS JSON output)

        [VALIDATION] If quality_report is missing any of these four fields, 
        do NOT invent values. Treat as "Verifier produces invalid standard 
        scores" or "Verifier fails to extract final_dus_score" error 
        (see Error Handling table).

    STEP 7.3: SAVE quality_report to "{{repository_name}}/.opencode/tmp/quality_report_iteration_{iteration_counter}.md"

    STEP 7.4: APPEND quality_report to quality_reports array

    STEP 7.5: APPEND score data to all_scores array:
        - iteration: iteration_counter
        - md_to_code: MD_to_Code_Score
        - code_to_md: Code_to_MD_Score
        - f_quality: F_Quality_Score
        - dus_score: final_dus_score

    STEP 7.6: CALCULATE composite_score via `metrics` tool:
        - Tool Invoked: `metrics.calculate_composite_score`
        - Inputs:
            - `md_to_code`: {MD_to_Code_Score}
            - `code_to_md`: {Code_to_MD_Score}
            - `dus`: {final_dus_score}

        [SOLE_METHOD] Use ONLY the `metrics.calculate_composite_score` tool. 
        Do NOT compute this formula in-line, in a script, or via any other 
        mechanism.

        IF composite_score > best_composite_score:
            - SET best_composite_score = composite_score
            - SET best_document_path = current_document_path

    STEP 7.7: CHECK EARLY EXIT CONDITIONS:
        IF (MD_to_Code_Score >= 0.65 AND Code_to_MD_Score >= 0.65 AND F_Quality_Score >= 0.65) AND final_dus_score >= 0.7:
            - BREAK loop

    STEP 7.8: IF iteration_counter == 5:
        - BREAK loop

    STEP 7.9: INCREMENT iteration_counter

    STEP 7.10: INVOKE code-summarizer
        - INPUT: repository_name = {{repository_name}}, quality_reports = quality_reports
        - OUTPUT: regenerated document

        [SERIALIZATION] This step MUST NOT start until Steps 7.1–7.9 of the 
        CURRENT iteration are complete. Do NOT pre-generate the next 
        iteration's document in parallel with verification.

        [SOLE_METHOD] This INVOKE is the ONLY valid way to produce a 
        documentation file.

        [FORBIDDEN] Do NOT copy, clone, symlink, or `cp` any previous 
        iteration's .md file to create the new document. Do NOT manually 
        edit a previous file. Every iteration's document MUST be a fresh 
        output from code-summarizer.

    STEP 7.11: SET current_document_path = "{{repository_name}}/.opencode/tmp/generated_document_iteration_{iteration_counter}.md"

    STEP 7.12: SAVE regenerated document to current_document_path

        [VALIDATION] After saving, verify the file exists and is non-empty 
        before proceeding to Step 7.1 of the next iteration. If empty or 
        missing, treat as "Generator produces empty document" error 
        (see Error Handling table).

    STEP 7.13: CONTINUE loop

END WHILE
```

### Phase 3: Final Selection

```
STEP 8: COPY best_document_path to {{repository_name}}/.opencode/generated_document.md

    [VALIDATION] Verify best_document_path is not null before copying. 
    If null, treat as "All iterations fail" error (see Error Handling table).

STEP 9: GENERATE pipeline_summary.md (see format below)

    [SOLE_METHOD] Generate this file directly as agent output. Do NOT 
    create a Python script to build it from all_scores array.

    [FORBIDDEN] Do NOT alter the "Iteration Comparison" table format. 
    The exact column structure (Iteration, F_Quality, MD_to_Code, 
    Code_to_MD, DUS Score, Composite, Status) is required. Do NOT add, 
    remove, or rename columns.

STEP 10: SAVE pipeline_summary.md to {{repository_name}}/.opencode/pipeline_summary.md

STEP 11: LOG "Pipeline complete. Final document: {{repository_name}}/.opencode/generated_document.md"
```

---

## Skill Invocation Protocol

### Generator Invocation

```
SKILL_ID: code-summarizer
TRIGGER_PHRASE: "Generate documentation for repository {repository_name}"
CONTEXT:
    - repository_name: string (required)
    - quality_reports: array of previous reports (optional, null on first run)
EXPECTED_OUTPUT:
    - Complete Markdown document content
    - JSON structure file at {repository_name}/.opencode/tmp/documentation_structure.json
```

### Verifier Invocation

```
SKILL_ID: md-verifier
TRIGGER_PHRASE: "Evaluate documentation at {document_path} against repository {repository_name}"
CONTEXT:
    - document_path: string (required)
    - repository_name: string (required)
EXPECTED_OUTPUT:
    - Quality report in specified markdown format
    - Must contain: MD_to_Code_Score, Code_to_MD_Score, F_Quality_Score
    - Must contain parsed JSON field: final_dus_score (from internal `dus` skill execution)
```

### Utility Tool Invocation Protocol

In addition to skills, this orchestrator has access to deterministic Python utility tools for calculations. 

**Tool 1: Composite Score Calculator**
```
TOOL_ID: metrics.calculate_composite_score
TRIGGER_PHRASE: "Calculate composite score using md_to_code, code_to_md, and dus"
INPUTS:
    - md_to_code (float): Precision/grounded truthness score (0.0 to 1.0)
    - code_to_md (float): Recall/document completeness score (0.0 to 1.0)
    - dus (float): Document usefulness score (0.0 to 1.0)
EXECUTION: Python script `metrics.py` -> `calculate_composite_score()`
EXPECTED_OUTPUT:
    - Float value representing the composite score.
    - Formula applied internally: (5 / 3) * (md_to_code + code_to_md + dus)
```

---

## Pipeline Summary Format

Generate `pipeline_summary.md` in the following format:

# Documentation Pipeline Summary

## Configuration
- **Repository:** {{repository_name}}
- **Max Iterations:** 5
- **Standard Thresholds:** MD_to_Code >= 0.65 AND F_Quality >= 0.65
- **DUS Threshold:** final_dus_score >= 0.7
- **Composite Formula:** (5/3) * (MD_to_Code + Code_to_MD + DUS)

## Execution Results

### Iteration Comparison

| Iteration | F_Quality | MD_to_Code | Code_to_MD | DUS Score | Composite | Status |
|-----------|-----------|------------|------------|-----------|-----------|--------|
| 1 | {score} | {score} | {score} | {score} | {score} | {Best/Not Best} |
| 2 | {score} | {score} | {score} | {score} | {score} | {Best/Not Best/Skipped} |
| 3 | {score} | {score} | {score} | {score} | {score} | {Best/Not Best/Skipped} |
| 4 | {score} | {score} | {score} | {score} | {score} | {Best/Not Best/Skipped} |
| 5 | {score} | {score} | {score} | {score} | {score} | {Best/Not Best/Skipped} |

### Final Selection
- **Selected Iteration:** {n}
- **Final Composite Score:** {score}
- **Thresholds Met:** {Yes/No}
- **Reason:** {All thresholds achieved / Max iterations reached - selected best composite score}

### Generated Files

| File | Path |
|------|------|
| Final Document | `.opencode/generated_document.md` |
| Iteration 1 Document | `.opencode/tmp/generated_document_iteration_1.md` |
| Iteration 1 Report | `.opencode/tmp/quality_report_iteration_1.md` |
| Iteration 2 Document | `.opencode/tmp/generated_document_iteration_2.md` |
| Iteration 2 Report | `.opencode/tmp/quality_report_iteration_2.md` |
| Iteration 3 Document | `.opencode/tmp/generated_document_iteration_3.md` |
| Iteration 3 Report | `.opencode/tmp/quality_report_iteration_3.md` |
| Iteration 4 Document | `.opencode/tmp/generated_document_iteration_4.md` |
| Iteration 4 Report | `.opencode/tmp/quality_report_iteration_4.md` |
| Iteration 5 Document | `.opencode/tmp/generated_document_iteration_5.md` |
| Iteration 5 Report | `.opencode/tmp/quality_report_iteration_5.md` |
| Pipeline Summary | `.opencode/pipeline_summary.md` |
| Doc Structure | `.opencode/tmp/documentation_structure.json` |
| Package Set | `.opencode/tmp/code_blocks.json` |

## Quality Progression

{If multiple iterations, describe how quality improved or changed between iterations, specifically noting MD-to-Code, F_Quality, and DUS improvements}

---

## Error Handling

| Error Condition | Action |
|-----------------|--------|
| Generator skill fails | Log error, retry once, then abort with current best document |
| Verifier skill fails | Log error, assume all scores = 0.0, continue to next iteration |
| Verifier fails to extract `final_dus_score` from DUS JSON | Log error, assume `final_dus_score` = 0.0, continue to next iteration |
| Generator produces empty document | Log error, skip iteration, continue with next |
| Verifier produces invalid standard scores | Log error, assume all scores = 0.0, continue to next iteration |
| All iterations fail | Output error report, no final document |
| All iterations score 0 | Output best available document with warning in summary |

---

## File Manifest

After successful pipeline execution:

```
{{repository_name}}/.opencode/
├── generated_document.md                    # Final selected document (BEST COMPOSITE)
├── pipeline_summary.md                      # Final execution summary
└── tmp/
    ├── generated_document_iteration_1.md    # Iteration 1 output
    ├── generated_document_iteration_2.md    # Iteration 2 output (if executed)
    ├── generated_document_iteration_3.md    # Iteration 3 output (if executed)
    ├── generated_document_iteration_4.md    # Iteration 4 output (if executed)
    ├── generated_document_iteration_5.md    # Iteration 5 output (if executed)
    ├── quality_report_iteration_1.md        # Iteration 1 quality report
    ├── quality_report_iteration_2.md        # Iteration 2 quality report (if executed)
    ├── quality_report_iteration_3.md        # Iteration 3 quality report (if executed)
    ├── quality_report_iteration_4.md        # Iteration 4 quality report (if executed)
    ├── quality_report_iteration_5.md        # Iteration 5 quality report (if executed)
    ├── code_blocks.json                     # JSON packages srtucture of project
    └── documentation_structure.json         # JSON structure from generator
```

---

## Integration Notes

1. **Entry Point:** This orchestrator skill is the ONLY entry point for documentation generation requests
2. **Skill Dependency:** Generator and Verifier skills should NOT be invoked directly by users
3. **Context Passing:** Quality reports from previous iterations are passed to generator as improvement context
4. **Statelessness:** Generator and Verifier are stateless — all state is managed by orchestrator
5. **File Ownership:** Orchestrator owns all file naming and storage decisions
6. **DUS Integration:** The `md-verifier` skill handles the internal invocation of the `dus` skill and parsing of its JSON payload to expose `final_dus_score` to this orchestrator.

---

## Invariants

These are non-negotiable properties that MUST hold at all times during execution. Each invariant exists because violating it produces a specific failure mode.

### INV-1: Skill Monopoly
**Rule:** Documentation content MUST be produced ONLY by invoking the `code-summarizer` skill. Scores MUST be produced ONLY by invoking the `md-verifier` skill. Composite scores MUST be produced ONLY by the `metrics.calculate_composite_score` tool.
**Reason:** Replacing skill invocations with hand-written scripts bypasses the quality logic, scoring logic, and DUS integration embedded in those skills, producing invalid outputs.
**Detection:** If any `.md` file in `.opencode/tmp/` was NOT created as direct OUTPUT of an `INVOKE code-summarizer` step, INV-1 is violated.

### INV-2: Strict Sequentiality
**Rule:** Within each iteration, the order MUST be: generate → save → verify → score → decide → (next generate). No two of these phases may overlap or run in parallel.
**Reason:** The verifier requires a complete, saved document on disk. The generator requires complete quality reports. Parallel execution produces file-not-found errors or stale-data scoring.
**Detection:** If iteration N's quality_report references a document that does not yet exist on disk, INV-2 is violated.

### INV-3: No Score Fabrication
**Rule:** A quality report for iteration J MUST NOT exist unless `generated_document_iteration_J.md` exists and was produced by `code-summarizer`. Scores MUST NOT be estimated, copied from other iterations, or invented.
**Reason:** Fabricated scores make the early-exit decision and final selection meaningless. The pipeline summary becomes misleading.
**Detection:** Count of quality_report files in `.opencode/tmp/` MUST equal count of generated_document files in `.opencode/tmp/`. If not, INV-3 is violated.

### INV-4: No Document Cloning
**Rule:** Each `generated_document_iteration_J.md` MUST be a fresh invocation output. Copying a previous iteration's file (via `cp`, file read+write, or any other mechanism) is prohibited.
**Reason:** Cloned documents produce identical scores, wasting iterations without improvement and violating the iterative refinement purpose.
**Detection:** If `generated_document_iteration_J.md` is byte-identical to any previous iteration file, INV-4 is violated.

### INV-5: Script Containment
**Rule:** Any helper scripts created during execution MUST be placed under `{{repository_name}}/.opencode/tmp/scripts/`. No scripts, logs, or temporary files may be written to the repository root, `src/`, or any other directory outside `.opencode/`.
**Reason:** The repository's source tree must remain clean. Users should be able to `git diff` and see only the `.opencode/` directory changed.
**Detection:** If any new `.py`, `.sh`, `.txt`, or `.log` file exists outside `.opencode/` after pipeline completion, INV-5 is violated.

### INV-6: No Pipeline Script Substitution
**Rule:** It is PROHIBITED to create any Python script whose purpose is to orchestrate, run, validate, coordinate, or otherwise replace the logic described in this skill's algorithm (Phases 0–3). This includes but is not limited to files named or described as: `pipeline_orchestrator.py`, `runner.py`, `validator.py`, `doc_pipeline.py`, `iterative_generator.py`, `score_aggregator.py`, or any script that performs looping, skill invocation routing, score comparison, or document selection.
**Reason:** This entire skill IS the orchestrator. Its algorithm is executed by the agent step-by-step via skill invocations and tool calls. A Python script that re-implements this loop bypasses the agent's skill dispatch mechanism, breaks context passing between skills, eliminates error handling granularity, and makes the pipeline opaque and undebuggable. The agent must REMAIN the orchestrator — not delegate orchestration to a script.
**Detection:** If any `.py` file under `.opencode/tmp/scripts/` (or anywhere else) contains loop constructs (`while`, `for`) combined with skill-triggering phrases (e.g., `"Generate documentation"`, `"Evaluate documentation"`, `"Calculate composite score`), file I/O to `.opencode/tmp/generated_document_iteration_*.md`, or score comparison logic (`if score > best`), INV-6 is violated.