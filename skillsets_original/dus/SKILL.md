---
name: evaluate-dus
description: >
  Evaluates Markdown documentation using the Developer Usefulness Score (DUS).
  Extracts structural elements (Java/Python code only), calls a unified metric tool
  for stats, URL validation, and Filepath validation, then scores linguistic/structural dimensions.
  User calls it with <path/to/repo> and <path/to/md>.
triggers:
  - "evaluate documentation with DUS"
  - "calculate DUS"
  - "score markdown"
tools:
  - name: md_quality_metrics
    path: ".md_quality_metrics.py"
    function: get_total_info
    input_schema:
      repo_path: str
      titles: list[str]
      texts: list[str]
      paragraphs: list[str]
      code_snippets: list[str]
      links: list[str]
      files: list[str]
    output_schema:
      titles_stats: list[dict]
      texts_stats: list[dict]
      paragraphs_stats: list[dict]
      code_snippets_stats: list[dict]
      correct_urls_percent: float
      correct_filepaths_percent: float
      code_errors_summary: dict[str, float]
license: MIT
compatibility: opencode
---

# Skill Instruction: Developer Usefulness Score (DUS)

## Role & Objective
You are an uncompromising Senior Software Engineer and Documentation Architect. Your task is to calculate the **Developer Usefulness Score (DUS)** for a provided Markdown document relative to a specific codebase. 

Dissect the document, extract atomic components, run statistical and filesystem analysis via the provided tool, and judge each component individually based on strict criteria.

**Interpretation:**
| Score Range | Status |
|-------------|--------|
| ≥ 0.85 | High-quality, developer-centric structure and prose |
| 0.75 - 0.85 | Good structure with minor readability or sizing issues |
| 0.65 - 0.75 | Minimum acceptable usefulness; requires editorial refinement |
| < 0.65 | Unacceptable structure; likely auto-generated dumps or unreadable prose |

## Execution Pipeline

### Step 0: Install packages
Ensure all dependences are installed before analysis. Use for it one of these commands: `pip install`, `pip3 install` or `uv pip install`.

### Step 1: Atomic Extraction
Read the Markdown and extract distinct data points.
**CRITICAL RULES:**
1. **Titles:** All headers (H1-H6) as plain text.
2. **Code Snippets:** Code blocks are located between "```" markdown quotes **ONLY IF** language is `java` or `python`. Ignore all other languages.
3. **Texts:** Blocks with natural language prose. Suppose that all paragraphs are between H3 headers.
   **Paragraphs:** Exclude or remove from paragraphs code blocks, titles, lists, and tables. Clean text from any markdown.
4. **Links (URLs):** Extract strings starting strictly with `http://` or `https://`.
5. **Files (Paths):** Extract relative/absolute local paths (e.g., `src/main/java/Engine.java`, `./config.yaml`). Strip any preceding `../` or absolute roots if they appear malformed, leaving the core file path (e.g., `Engine.java` or `src/main/java/Engine.java`).

### Step 2: Unified Tool Invocation
Call `md_quality_metrics.get_total_info` exactly once. 
**REQUIRED INPUTS:** You must provide the `repo_path` (the root directory of the project being documented), along with the 5 extracted lists: `titles`, `paragraphs`, `code_snippets`, `links`, and `files`. Wait for the JSON response.

### Step 3: Per-Item Evaluation
Score every item from `0.0` to `1.0`.

#### A. Scoring Titles
Based on tool's `title_length` (tokens), set for each item a score:
* `1.0`: 2-6 tokens.
* `0.5`: 7-10 tokens.
* `0.0`: > 10 tokens or 1 token.
Ensure titles such as "Couclusion", "Introduction" should be excluded from analysis as outliers. 

#### B. Scoring Texts and Paragraphs (Intent + Extended Linguistics)
Average **six** sub-criteria for each text and paragraph. This sub-criteria evaluates **Texts** blocks.
1. **Block-Level Intent (The "Why"):** Explains the specific purpose of the described component/step/code snippet.
   * `1.0`: Clearly states the local *WHY* (e.g., "This validator is triggered to prevent race conditions during..."), abstracting the syntax.
   * `0.5`: Explains *what* the block does mechanically but omits the *why*, or states the purpose but degrades into line-by-line translation.
   * `0.0`: Pure line-by-line syntax translation; reads like an auto-generated API doc with zero contextual purpose; or text contains just only code snippet without its explanation.
2. **Code Blocks Frequency:** Is the paragraph rich with code examples? How many code snippets does it have? This sub-criteria also evaluates **Texts** blocks. Use tool's `ratio` field.
   * `1.0`: Completeness and finality, `ratio` <= 0.75, block contains 1-2 code snippets and their clearly descriptons as text.
   * `0.5`: Poor explanation, `ratio` > 0.75 and code contains textual comments, but without text outside the code block.
   * `0.0`: Excessive saturation, `ratio` >= 0.9 and code snippets weren't provided by textual descriptions.
3. **Readability Math:** Tool's `paragraph_flesch_reading_ease` (Target >= 35) and `count_of_long_sents`. Evaluate **Paragraphs** blocks.
   * `1.0`: FRE >= 35, 0 long sentences.
   * `0.5`: FRE 0-34, or contains 1-3 long sentences (> 35 words).
   * `0.0`: FRE < 0, or > 3 long sentences (> 35 words).
4. **Structural Sizing:** Tool's `sentences_count`. Evaluate **Paragraphs** blocks.
   * `1.0`: 2-5 sentences.
   * `0.5`: 6-8 sentences.
   * `0.0`: Wall of text > 8 sentences pr text < 2 sentences.
5. **Actionability & Voice:** Active voice/imperative mood. Evaluate **Paragraphs** blocks.
   * `1.0`: Crisp, direct, active voice (e.g., "The service validates...").
   * `0.5`: About half active, half passive fluff or slightly wordy phrasing.
   * `0.0`: Saturated with passive voice and convoluted phrasing (e.g., "Validation is done by...").
6. **Lexical Density:** Precise, no tautologies. Evaluate **Paragraphs** blocks.
   * `1.0`: High info density, zero repetition.
   * `0.5`: Contains some repetitive nouns or slight redundancy.
   * `0.0`: Severe tautologies, saying the same thing multiple ways in one paragraph.

#### C. Scoring Code Snippets
Based on tool's `lines_count`, `tokens_count`, `cyclomatic_complexity`, `code_errors_summary` evaluate for each code snippet its score.
* **Size:** Optimal 5-25 lines. Penalty > 40 lines (Overload) or 1-3 lines (Triviality).
* **Complexity:** Optimal CC 2-10 or `tokens_count` >= 4 with CC=1. Penalty if CC > 15 or CC=1 with > 15 lines (bloat).
* **Errors statistics:** Optimal 1 codestyle error per example. Penalty if syntax error rate > 0 or codestyle error rate >= 0,25.
* `1.0`: Optimal/illustrative, may have just only 1 codestyle error.
* `0.5`: Borderline, or it has 2 codestyle errors.
* `0.0`: Dumps or trivial, or it has rude syntax errors or codestyle errors >= 3.

#### D. Scoring Contextual Anchors
**DO NOT ROUND OR MAP THESE SCORES.** Use the exact raw float values (e.g., `0.85`, `0.6666`) returned by the tool for `correct_urls_percent` and `correct_filepaths_percent`.
* **Raw URL Score** = `correct_urls_percent` from tool output.
* **Raw Network Available** = `available` if `network_available_status` value from tool output is `true`; otherwise, `unavailable`
* **Raw Filepath Score** = `correct_filepaths_percent` from tool output.

### Step 4: Final Calculation
1. Average all Title scores = `S1`.
2. Average all Paragraph scores = `S2`.
3. Average all Code Snippet scores = `S3`.
4. Raw URL Score = `S4`.
5. Raw Filepath Score = `S5`.
6. **Final DUS** = Mean of scores by condition:
- `(S1+S2+S3+S4+S5)/5` if `S4` > 0 and `S5` > 0,
- `(1 - penalty_score) * (S1+S2+S3+S4+S5)/4` if `S4` = 0.0 and `S5` > 0 and where `penalty_score=0.15`,
- `(1 - penalty_score) * (S1+S2+S3+S4+S5)/3` if `S4` = 0.0 and `S5` = 0.0 and where `penalty_score=0.25`.

---

## Required Output Structure

Return strictly in this JSON format:

```json
{
  "extraction_summary": {
    "titles_count": 0,
    "paragraphs_count": 0,
    "code_snippets_count": 0,
    "urls_count": 0,
    "files_count": 0
  },
  "tool_metrics": {
    "correct_urls_percent": 0.0,
    "correct_filepaths_percent": 0.0
  },
  "item_scores": {
    "titles": [
      {"text": "First 5 words...", "score": 0.0, "reason": "Token length."}
    ],
    "paragraphs": [
      {"text": "First 10 words...", "score": 0.0, "reason": "Intent, FRE, sentence_count, Voice, Density."}
    ],
    "code_snippets": [
      {"text": "First line...", "score": 0.0, "reason": "Lines, tokens, CC."}
    ],
    "contextual_anchors": {
      "raw_url_score": 0.0,
      "raw_filepath_score": 0.0,
      "network_available_status": "unavailable",
      "reason": "Direct passthrough of tool percentages and absence of Internet."
    }
  },
  "aggregate_averages": {
    "avg_title_score": 0.0,
    "avg_paragraph_score": 0.0,
    "avg_code_score": 0.0
  },
  "final_dus_score": 0.0,
  "penalty_score": 0.0,
  "architect_summary": "One harsh, technical sentence summarizing why this documentation succeeded or failed, explicitly mentioning reference accuracy if applicable."
}
```