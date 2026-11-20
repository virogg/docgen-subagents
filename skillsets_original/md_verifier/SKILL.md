---
name: md-verifier
description: "Evaluate quality of a generated MD document against the codebase, including structural coherence via DUS. Use when the user asks to verify documentation for the project by path <path/to/repo>/.opencode/generated_documentation.md."
triggers:
  - "validate documentation"
  - "calculate quality of MD"
  - "estimate markdown quality"
tools:
  - name: verifier_utils
    path: ".verifier_utils.py"
    functions:
      - name: calculate_correct_verdicts_ratio
        description: "Calculates the ratio of 'yes' answers in a list of verdicts. Each verdict is a dict with an 'answer' key equal to 'yes' or 'no'. Use when evaluating how many documentation blocks passed verification."
        input_schema:
          type: object
          properties:
            verdicts:
              type: array
              items:
                type: object
                properties:
                  answer:
                    type: string
                    description: "Either 'yes' or 'no'."
          required:
            - verdicts
        output_schema:
          type: object
          properties:
            ratio:
              type: number
   
      - name: calculate_coverage_adjusted_fidelity
        description: "Calculates the coverage-adjusted fidelity score for MD-to-Code evaluation. Computes the ratio of 'yes' answers in a list of verdicts, adjusting based on the document's properties. Use in Metric 1 (MD-to-Code Fidelity) specifically for evaluating how many documentation claims are grounded in the codebase."
        input_schema:
          type: object
          properties:
            verdicts:
              type: array
              items:
                type: object
                properties:
                  answer:
                    type: string
                    description: "Either 'yes' or 'no'."
            md_doc_path:
              type: string
              description: "Absolute path to the generated Markdown documentation file being evaluated."
          required:
            - verdicts
            - md_doc_path
        output_schema:
          type: object
          properties:
            ratio:
              type: number
              description: "The calculated fidelity score (0.0 to 1.0)."

      - name: calculate_f_quality_score
        description: "Computes F-beta score (beta=0.75) balancing precision (md_to_code: grounded truthness) and recall (code_to_md: documentation completeness). Beta below 1 slightly favors precision. Use when combining both metrics into a single quality score."
        input_schema:
          type: object
          properties:
            md_to_code:
              type: number
              description: "Precision — grounded truthness score (0.0 to 1.0)."
            code_to_md:
              type: number
              description: "Recall — documentation completeness score (0.0 to 1.0)."
          required:
            - md_to_code
            - code_to_md
        output_schema:
          type: object
          properties:
            f_score:
              type: number
   
      - name: codebase_to_blocks
        description: "Deterministically extracts key architectural Java blocks (packages, public top-level classes/interfaces/enums, and @Override/main methods) grouped by package namespace. Use in Phase 2 of Code-to-MD evaluation."
        input_schema:
          type: object
          properties:
            repository_path:
              type: string
              description: "The root directory path of the repository to analyze."
          required:
            - repository_path
        output_schema:
          type: array
          items:
            type: object
            properties:
              package_id:
                type: string
                description: "Unique ID for the package, e.g., P001"
              package_name:
                type: string
                description: "Java package identifier, e.g., io.github.jbellis.jvector.vector"
              key_indicator:
                type: string
                description: "Always 'package_directory' for top-level items"
              info:
                type: array
                description: "List of key components (classes, interfaces, key methods) inside this package."
                items:
                  type: object
                  properties:
                    block_id:
                      type: string
                    type:
                      type: string
                      description: "class, interface, enum, or method"
                    name:
                      type: string
                    file:
                      type: string
                    key_indicator:
                      type: string
                      description: "e.g., 'public class', 'public interface', '@Override'"
license: MIT
compatibility: opencode
---

# Documentation Quality Evaluator

## Role

As a technical documentation analyst, you are responsible for evaluating a single generated Markdown document against the actual codebase and producing a quality report with precise metrics. You must also invoke the separate `evaluate-dus` skill to evaluate structural coherence and aggregate its results into your final report.

## Input Parameters

- `document_path`: Path to the MD file to evaluate
- `repository_name`: Path to the codebase

## Output

Quality report containing:
- `MD_to_Code_Score`: Fidelity metric (0.0 - 1.0)
- `Code_to_MD_Score`: Coverage metric (0.0 - 1.0)
- `F_Quality_Score`: Harmonic quality metric (0.0 - 1.0)
- `final_dus_score`: Structural coherence metric extracted from `evaluate-dus` skill JSON (0.0 - 1.0)
- Detailed block-by-block analysis
- Improvement recommendations

### Install packages
Ensure all dependences are installed before analysis. Use for it one of these commands: `pip install`, `pip3 install` or `uv pip install`.

---

## Metric 1: MD-to-Code Fidelity Score (Documentation Grounding)

**Objective:** Verify that all content blocks in the MD-documentation have corresponding evidence in the codebase, detecting hallucinations and fabricated content.

**Procedure:**

1. Parse the Markdown documentation into factual claims. To ensure stable evaluation across iterations, strictly adhere to these extraction boundaries:
   - **One claim per distinct sentence.** Do not combine two sentences into one claim.
   - **Code blocks count as a single claim.** (e.g., "The file contains a class `UserService` with method `login()`" is ONE claim, regardless of how long the code block is).
   - **List items:** Each bullet point in a list is a separate claim.
   - **DO NOT SKIP sections.** You must process the document sequentially from top to bottom.
2. For each claim X extracted from the MD-file:
   - Extract key elements (class names, method names, file paths, code snippets, architectural descriptions)
   - Search the entire codebase for corresponding evidence
   - Claim X is considered "found in codebase" if a matching fragment Y is discovered in the repository code
   - Matching criteria:
     - Exact match on class/method names, file paths, structural components, or code fragments.
     - If both claim X and fragment Y contain natural language text: evaluate semantic overlap. The match is considered valid if the core meaning, subject, and key terminology align directly without fabricating new concepts (equivalent to high semantic similarity).
3. Construct a `verdicts` list where each claim becomes a dictionary: `{"answer": "yes"}` if found in the codebase, or `{"answer": "no"}` if not.
4. Invoke the `calculate_coverage_adjusted_fidelity` function from the `verifier_utils` tool, passing the constructed `verdicts` list and absolute path to MD documentation.
5. Extract the returned `ratio` value and assign it to `MD_to_Code_Score`.

**Interpretation:**
| Score Range | Status |
|-------------|--------|
| ≥ 0.85 | Excellent documentation grounding |
| 0.65 - 0.85 | Good documentation with minor hallucinations |
| < 0.65 | Significant hallucinations requiring revision |

---

## Metric 2: Code-to-MD Coverage Score (Documentation Completeness)

**Objective:** Evaluate the completeness of documentation by using Tree-sitter to deterministically extract key Java architectural blocks (grouped by package), and measuring their coverage in the MD document.

**Available Analytical Tools:**
- `tree-sitter` parser via Python execution tool (using `tree-sitter` bindings and `tree-sitter-java`).
- `verifier_utils` tool containing the `codebase_to_blocks` and `calculate_correct_verdicts_ratio` functions.

**CRITICAL CONSTRAINT:** 
You are strictly forbidden from mentally parsing the codebase or guessing logical blocks. You must use a deterministic, tool-execution process: invoke the Python extraction script against the repository path, capture the exact JSON output, and evaluate it.

**Procedure:**

### Phase 1: Path Scoping
1. Identify the root directory of the `{{repository_name}}` repository.
2. Explicitly ignore paths containing `build/`, `target/`, `test/` (if evaluating main documentation only), `.gradle/`, or `.mvn/`. *(Note: The extraction script handles this automatically, but be aware of these boundaries).*

### Phase 2: Deterministic Extraction & Grouping
0. Firstly, check if `{{repository_name}}/.opencode/tmp/code_blocks.json` already exists; it is possible when if `{{repository_name}}/.opencode/tmp/` folder has at least one `quality_report_iteration_X.md` filse. Otherwise, execute steps 1-5 in the current Phase.
1. Invoke your Python execution tool.
2. Execute the `codebase_to_blocks` function (provided in your environment), passing the repository root path as the argument.
3. The script will automatically apply **Pure Java Significance Filters**:
   - **Classes/Interfaces/Enums:** INCLUDE only top-level `public` types. EXCLUDE package-private, inner, and anonymous classes.
   - **Methods:** INCLUDE only `@Override` methods and `public static void main`. EXCLUDE all other public/protected/private methods, getters, setters, `toString`, `hashCode`, and `equals`.
4. **CRITICAL OUTPUT FORMAT:** Capture the exact JSON array returned by the script. It groups components by their package namespace. The structure will look exactly like this:
```json
[
  {
    "package_id": "P001",
    "package_name": "package_name",
    "key_indicator": "package_directory",
    "info": [
      {
        "block_id": "B001",
        "type": "class",
        "name": "MyClass",
        "file": "package_name/src/main/java/.../MyClass.java",
        "key_indicator": "public class"
      },
      {
        "block_id": "B002",
        "type": "method",
        "name": "foo",
        "file": "package_name/src/main/java/.../MyClass.java",
        "key_indicator": "@Override"
      }
    ]
  }
]
```
5. Save result structure to this file `{{repository_name}}/.opencode/tmp/code_blocks.json`.

### Phase 3: Package-Level Coverage Evaluation
1. Define `TOTAL_BLOCKS` as the total number of package objects in the root JSON array.
2. Iterate through each package object. For each Package X:
   - Search the generated MD-documentation for the `package_name`.
   - Evaluate if the MD file explains the architectural purpose of this package.
   - Evaluate if the MD file acknowledges or describes the core components listed in the `info` array. *(Note: It does NOT need to describe every single method in the `info` array, but it MUST describe the primary public classes/interfaces and the overall purpose of the package's components).*
   - **Verdict Logic:** Package X is considered "documented" (`yes`) ONLY if the MD explicitly describes the package's purpose AND covers its core components. If the package is completely missing, or if only a bare filepath/package name/code example is mentioned without explaining what the package does, it is undocumented (`no`).
3. Construct a `verdicts` list containing one dictionary per package, e.g., `[{"answer": "yes"}, {"answer": "no"}]`.
4. Invoke the `calculate_correct_verdicts_ratio` function from the `verifier_utils` tool, passing the constructed `verdicts` list.
5. Extract the returned `ratio` value and assign it to `Code_to_MD_Score`.

**Interpretation:**
| Score Range | Status |
|-------------|--------|
| ≥ 0.85 | Comprehensive documentation coverage (Architecture is well explained) |
| 0.65 - 0.85 | Adequate coverage with gaps (Some packages lack high-level explanations) |
| < 0.65 | Insufficient documentation coverage (Missing package-level context) |


**Note:** While the Code_to_MD_Score is calculated at the package level, you must still use the extracted individual block_ids (e.g., B001, B002) to populate the 'Detailed Block Analysis' table in the final report, marking them as 'Yes' or 'No' based on whether their parent package was marked as documented.

---

## Metric 3: Harmonic Quality Score (Overall Documentation Quality)

**Objective:** Calculate a single comprehensive quality metric that balances both grounding and completeness using the F-beta formula.

**Procedure:**
1. Take the calculated `MD_to_Code_Score` (from Metric 1).
2. Take the calculated `Code_to_MD_Score` (from Metric 2).
3. Invoke the `calculate_f_quality_score` function from the `verifier_utils` tool.
   - Pass `MD_to_Code_Score` as the `md_to_code` argument.
   - Pass `Code_to_MD_Score` as the `code_to_md` argument.
4. Extract the returned `f_score` value and assign it to `F_Quality_Score`.

**Properties:**
- Uses F-beta score with beta=0.75 (slightly favoring precision/grounding over recall/completeness).
- Harmonic mean penalizes imbalance between the two metrics.
- Both grounding and completeness must be strong to achieve a high score.
- Range: 0.0 to 1.0

**Interpretation:**
| Score Range | Status |
|-------------|--------|
| ≥ 0.85 | High quality production documentation |
| ≥ 0.75 | Good quality documentation |
| ≥ 0.65 | Minimum acceptable documentation quality |
| < 0.65 | Unacceptable documentation quality |

---

## Metric 4: DUS Structural Coherence Score (via `evaluate-dus` skill)

**Objective:** Evaluate the document's structural coherence and logical flow using the dedicated `evaluate-dus` skill.

**Procedure:**
1. Invoke the sibling `evaluate-dus` skill, passing the current `document_path` and `repository_name`:
   ```
    skill "evaluate-dus" <document_path> <repository_name>
   ```
3. The `evaluate-dus` skill will return a JSON object.
4. Strictly parse the JSON payload and extract the value of the `final_dus_score` key.

**Interpretation:**
| Score Range | Status |
|-------------|--------|
| ≥ 0.85 | Excellent structural coherence |
| 0.70 - 0.85 | Good structural coherence |
| < 0.70 | Poor structural coherence requiring revision |

---

## Quality Report Format

Generate the quality report in the following markdown format:

# Quality Report

## Evaluation Summary

| Metric | Score | Status |
|--------|-------|--------|
| MD_to_Code_Score | {value} | {interpretation} |
| Code_to_MD_Score | {value} | {interpretation} |
| F_Quality_Score | {value} | {interpretation} |
| final_dus_score | {value} | {interpretation} |

## Evaluated Document
- **Path:** {document_path}
- **Repository:** {repository_name}

## Hallucinated Content Blocks

### Block {n}
- **Location:** Section "{section_name}", paragraph {m}
- **Content Preview:** "{first 100 characters}..."
- **Issue:** {description of why block has no codebase evidence}
- **Expected Evidence:** {what should exist in codebase to validate this}

*(Repeat for each hallucinated block, or state "None detected" if applicable)*

## Undocumented Code Components

### Component {n}
- **Type:** {Class/Method/Interface/Config}
- **Name:** {component_name}
- **Location:** {file_path}:{line_range}
- **Missing Documentation:** {description of what is not documented}

*(Repeat for each undocumented component, or state "None detected" if applicable)*

## Detailed Block Analysis

| Block ID | Type | Found in Codebase | Notes |
|----------|------|-------------------|-------|
| B001 | Class description | Yes/No | {notes} |
| B002 | Method signature | Yes/No | {notes} |
| ... | ... | ... | ... |

## Improvement Recommendations

### Priority 1 - Critical
- {recommendation}

### Priority 2 - Important
- {recommendation}

### Priority 3 - Optional
- {recommendation}

## Metrics Calculation Details

### MD-to-Code Breakdown
- Total content blocks extracted: {n}
- Blocks found in codebase (verdicts: "yes"): {m}
- Blocks not found (verdicts: "no"): {k}
- Absolute path to MD: {absolute_path_to_md}
- Tool Invoked: `verifier_utils.calculate_coverage_adjusted_fidelity`
- MD_to_Code_Score: {value}

### Code-to-MD Breakdown
- Total code blocks/entities/packages extracted: {n}
- Documented code blocks/entities/packages (verdicts: "yes"): {m}
- Undocumented code blocks/entities/packages (verdicts: "no"): {k}
- Tool Invoked: `verifier_utils.calculate_correct_verdicts_ratio`
- Code_to_MD_Score: {value}

### Harmonic Quality Calculation
- Tool Invoked: `verifier_utils.calculate_f_quality_score`
- Inputs: `md_to_code`={MD_to_Code_Score}, `code_to_md`={Code_to_MD_Score}
- F_Quality_Score: {value}

### DUS Score Breakdown
- Source: `evaluate-dus` skill invocation
- Extracted JSON Field: `final_dus_score`
- final_dus_score: {value}

---

## Evaluation Procedure

Execute the following steps in order:

```
STEP 1: Load and parse the MD document at document_path
STEP 2: Load and parse the codebase at repository_name
STEP 3: Extract all content blocks (claims) from the MD document
STEP 4: For each MD block, search for codebase evidence and build fidelity verdicts list [{"answer": "yes"}, {"answer": "no"}]
STEP 5: INVOKE verifier_utils.calculate_coverage_adjusted_fidelity(verdicts=verdicts, md_doc_path=absolute_path_to_md) → MD_to_Code_Score
STEP 6: INVOKE verifier_utils.codebase_to_blocks(repository_path=repository_name) to get the JSON array of packages and components
STEP 7: For each package in the extracted JSON, search the MD for coverage and build coverage verdicts list [{"answer": "yes"}, {"answer": "no"}]
STEP 8: INVOKE verifier_utils.calculate_correct_verdicts_ratio(verdicts=verdicts) → Code_to_MD_Score
STEP 9: INVOKE verifier_utils.calculate_f_quality_score(md_to_code=MD_to_Code_Score, code_to_md=Code_to_MD_Score) → F_Quality_Score
STEP 10: INVOKE evaluate-dus skill
    - INPUT: document_path = {document_path}, repository_name = {repository_name}
    - OUTPUT: dus_result_json
STEP 11: PARSE dus_result_json and EXTRACT final_dus_score
STEP 12: Generate quality report in specified format (including final_dus_score, and mapping individual block IDs from STEP 6 into the Detailed Block Analysis table)
STEP 13: Output the report
```
---

## Restrictions
- It is STRICTLY prohibited to make changes to the MD documentation for improving the metric's value.
- It is STRICTLY prohibited to add any information about the quality to MD file.
- Generation of short quality reports is forbidden.
- The generated quality report is short if it doesn't contain one of next sections:
  **1.** A table with scores;
  **2.** Detailed block analysis;
  **3.** Breakdown block for metrics;
  **4.** A block with improvement recommendations.

---

## Output Destination

Output the quality report directly to stdout. 
