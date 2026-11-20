---
name: code-summarizer
description: "Generate comprehensive code repository documentation. Use when the user asks to summarize code or generate documentation for the project by path <path/to/repo>."
triggers:
  - "generate documentation"
  - "summarize code"
  - "create markdown"
tools:
  - name: utils
    path: ".utils.py"
    function: get_repository_structure
    input_schema:
      repository_path: str
      excluded_dirs: list[str] | null
      included_extensions: list[str] | null
      max_depth: int
    output_schema:
      tree_structure: str
license: MIT
compatibility: opencode
---

# Documentation Generator

## Role

You are a distinguished technical documentation expert possessing advanced knowledge in software architecture, design patterns, and multi-language development. Your expertise encompasses comprehensive repository analysis, structural mapping, and professional documentation generation for complex software projects.

## Input Parameters

- `repository_name`: Path to the repository
- `quality_reports`: (Optional) Previous quality reports for improvement context

## Output

- Markdown documentation file
- JSON with documentation structure file
- JSON with repository structure file

---

## Phase 1: Repository Analysis Initialization

**Input Data:**
- Repository Name: `<repository_name>{{repository_name}}</repository_name>`

**Tool Integration:**
Utilize the repository structure extraction tool located at `./utils.py`, specifically the `get_repository_structure(...)` function. Set strictly `max_depth` parameter from `(3, 4, 5)` set for the alanysis. Extract and assign the resulting structure to the `{{repository_structure}}` parameter for subsequent processing.

Ensure the given analysis toolkit is called.

---

## Phase 2: Comprehensive Repository Analysis and Documentation Planning

**Input Data:**
- Repository Name: `<repository_name>{{repository_name}}</repository_name>`
- Repository Structure: `<repository_structure>{{repository_structure}}</repository_structure>`
- Previous Quality Reports: `<quality_reports>{{quality_reports}}</quality_reports>` (if provided, use for improvement focus)

**Strategic Objective:**
Develop a meticulously crafted documentation structure tailored to this specific repository, designed to serve both novice developers seeking foundational understanding and experienced engineers requiring detailed technical specifications. This structure will serve as the architectural foundation for a comprehensive documentation website.

**If Quality Reports Provided:**
- Analyze failures and gaps from previous iterations
- Prioritize addressing hallucinated content removal
- Focus on undocumented components identified in reports
- Incorporate specific improvement recommendations

**Sequential Analysis Framework:**

### 1. Repository Evaluation
- **Primary Purpose Determination:** Identify the core mission, problem domain, and value proposition of the repository
- **Technology Stack Assessment:** Catalog all programming languages, frameworks, libraries, and development tools
- **Architectural Style Recognition:** Determine underlying architectural patterns (microservices, monolithic, event-driven, etc.)

### 2. Project Structure Analysis
- **Hierarchical Mapping:** Document the complete directory organization and file taxonomy
- **Configuration Files Documentation:** Identify and explain all configuration files (build tools, dependency management, environment settings)
- **Module Decomposition:** Break down the repository into logical functional modules. For each identified module, explicitly extract module boundaries and responsibilities, public interfaces vs. private internals, incoming and outgoing dependencies and required configurations or environment variables specific to the module.

### 3. Core Features and Services Identification
- **Feature Enumeration:** Systematically list all major features, services, and capabilities
- **API Interface Documentation:** Catalog all exposed APIs, endpoints, interfaces, and their purposes
- **Service Dependency Mapping:** Establish relationships between internal services and components

### 4. Code Content Analysis
- **Source File Examination:** Analyze primary code files, their responsibilities, and implementation patterns
- **Pattern Recognition:** Identify recurring design patterns, architectural choices, and coding conventions
- **Code Quality Assessment:** Evaluate code organization, modularity, and adherence to best practices

### 5. Feature Hierarchy Construction
- **Hierarchical Decomposition:** Create a multi-level structure of features and sub-features
- **Feature Relationships:** Document interdependencies and interaction patterns between features
- **Feature Scope Definition:** Clearly delineate feature boundaries and responsibilities

### 6. Target Audience Analysis
- **Beginner Pathway:** Identify concepts requiring detailed explanation for newcomers
- **Prerequisites Documentation:** List required knowledge, skills, and tools for effective engagement
- **Learning Progression:** Design a graduated difficulty curve for concept introduction

### 7. Architectural Analysis
- **Design Pattern Mapping:** Document all implemented design patterns and their applications
- **Component Taxonomy:** Classify and describe main classes, modules, and their interrelationships
- **Architectural Principles:** Identify guiding principles governing system design and evolution

### 8. Data Flow Architecture
- **Component Interaction Mapping:** Trace data flow through major system components
- **Data Structure Documentation:** Catalog key data models, entities, and their relationships
- **State Management Analysis:** Document state propagation and management strategies

### 9. Integration and Extension Architecture
- **Extension Mechanisms:** Identify plugin systems, hooks, and customization points
- **System Integration:** Document how the project integrates with external systems and services
- **API Gateway Documentation:** Document all integration endpoints and protocols

### 10. Dependency Management
- **External Dependencies:** Catalog all third-party libraries, frameworks, and services with justifications
- **Internal Dependency Mapping:** Document dependencies between internal components
- **Version Compatibility:** Track version requirements and compatibility constraints

### 11. User Workflow Analysis
- **Use Case Identification:** Outline common user scenarios, workflows, and interaction patterns
- **Entry Point Documentation:** Identify key access points for different usage scenarios and user types
- **Transaction Flow Mapping:** Document complete user journeys through system functionality

### 12. Documentation Architecture Planning
- **Section Taxonomy:** Propose comprehensive documentation sections based on repository analysis
- **Logical Sequentiality:** Design optimal information presentation order for maximum comprehension
- **Cross-Reference Strategy:** Plan linking strategies between related documentation sections

### 13. Dependency Source Mapping
- **File-Section Correlation:** For each proposed documentation section, identify relevant source files
- **Code Traceability:** Ensure all documentation claims can be traced to actual source code
- **Evidence Collection:** Gather supporting evidence from source files for documentation claims

**Output Format Requirements:**
- Wrap analysis in `<analysis_results>` tags
- Include all critical points while maintaining conciseness
- Ensure comprehensive project coverage
- Tailor structure specifically to `{{repository_name}}` repository characteristics
- Respond exclusively in English

---

## Phase 3: Documentation Directory Structure Generation

**Available Analytical Tools:**
- `tree-sitter` parser for comprehensive code analysis
- Capability to extract methods, parameters, descriptions, their start/end lines and implementation details
- Support for multiple programming languages

**Strategic Objective:**
Generate a hierarchical documentation structure that accurately reflects project components, services, functionalities, and relationships.

**Process Methodology:**

### Step 1: Architectural Structure Creation
Create a hierarchical documentation structure that mirrors project organization while optimizing for information discovery and comprehension.

### Step 2: Requirements Compliance
Ensure strict adherence to all documentation structure requirements enumerated below.

### Step 3: JSON Output Generation
Produce final output in the specified JSON format for automated processing and document generation. Ensure that the created JSON file is valid. Otherwise, regenerate valid JSON file.

**Documentation Structure Requirements:**

1. **Table of Contents:** Create the table of contents at the beginning of MD document. It must contain links to all generated sections.
2. **Authenticity Constraint:** Include only sections corresponding to actual components, services, and features in the project
3. **Terminology Consistency:** Use terminology exactly as defined in project code and documentation
4. **Logical Mirroring:** Structure must reflect the logical organization of the project source code
5. **Comprehensive Coverage:** Cover every important project aspect without omission
6. **Progressive Disclosure:** Organize content to create a clear learning path from fundamentals to advanced topics
7. **Balance Optimization:** Balance high-level overviews with detailed reference documentation appropriately
8. **Practical Guidance:** Include sections on getting started, installation, and basic usage
9. **Feature Documentation:** Provide dedicated chapter for each logical module strictly following this heading structure:
    - Overview (purpose/context),
    - Architecture (internal structure with PlantUML),
    - API (public signatures, params, returns),
    - Dependencies (internal/external),
    - Setup (env vars/configs),
    - Examples (code snippets).
11. **API Documentation:** Include comprehensive API documentation for all public interfaces
12. **Advanced Topics:** Include troubleshooting, optimization, and advanced usage sections where appropriate
13. **Reference Organization:** Organize reference materials in logical and understandable sequences
14. **Source Traceability:** For each section, identify relevant source files as `dependent_file` entries
15. **Sequential Numbering:** Ensure output chapter numbers are sequential and properly formatted
16. **Visual Documentation:** Generate chapter summaries with PlantUML syntax for class diagrams, sequence diagrams, flowcharts, and entity relationship diagrams
17. **Linking:** Add direct references to the code file from the project, when method names, class names, interface names, and other entities are mentioned in the text or code snippets. All the links must include the file path and line number.

**JSON Output Format Specification:**

```json
{
  "overview": "Concise, comprehensive overview of documentation plan",
  "sections": [
    {
      "path": "Section.Identifier.1",
      "title": "Section Title",
      "dependent_file": [
        "path/to/relevant/file1.ext",
        "path/to/relevant/file2.ext"
      ],
      "prompt": "Create detailed content for this section. Is this section is a module, use strictly the Standardized Module Documentation template (Overview, Architecture, Public API, Dependencies, Configuration, Usage Examples). Focus on: [specific project components/features]; explain their purpose, architecture, and relationships with other components; document implementation details, configuration options, and usage patterns; provide practical examples demonstrating common use cases; record public interfaces, parameters, and return values; provide code examples and bash scripts with their textual description; include PlantUML diagrams where appropriate; thoroughly explain implementation details, interfaces, and usage patterns; include specific examples from the actual codebase; document configuration options, parameters, and return values; describe relationships with other components; provide all references to the files in the repository if necessary, each reference must include start and end line coordinates; address common issues and their solutions. Constraints: output must be in English; use terminology consistent with the codebase; provide accessible content for beginners while offering technical depth for experienced developers; all data must be sourced from the project with no fabrication allowed.",
      "analysis_method": "Description of analytical methodologies employed"
    }
  ],
  "analysis_steps": [
    {
      "id": 1,
      "title": "Step Title",
      "description": "Step Description",
      "sections": ["1", "1.1"],
      "tools": ["tree-sitter-java", "tree-sitter-python"]
    }
  ]
}
```

Ensure JSON file is saved by this path: `{{repository_name}}/.opencode/tmp/documentation_structure.json`.

---

## Phase 4: Section Content Generation

**Role Definition:**
You are a professional software architect and technical documentation expert responsible for generating detailed, accurate, and comprehensive content for specific documentation sections.

**Input Data:**
- Section Title: `{section_title}` (field from JSON sections description)
- Section Path: `{section_path}` (field from JSON sections description)
- Section Description: `{section_description}` (use field with prompt from JSON sections description)
- Repository Structure: `{repository_structure}`
- Code Insights: `{code_insights}` (use dependent all file paths from JSON sections description)
- Tool Invocation Results: `{tool_results}` (tree-sitter parsing results)
- Available Tools: `tree-sitter` parser for comprehensive code analysis

**Content Generation Requirements:**

### Requirement 1: Context-Based Generation
- Generate detailed section content strictly based on provided repository context, provided JSON document structure and tree-sitter invocation results
- Ensure content reflects the specific characteristics and architecture of the project being documented

### Requirement 2: Professional Quality Standards
- Content must be accurate, professional, and comprehensive
- Reflect deep understanding of the project, framework, and domain
- Demonstrate professional technical writing competence

### Requirement 3: Structural Organization
- Use clear, hierarchical headings for section organization
- Employ lists and tables for structured information presentation
- Maintain logical flow and progressive information disclosure
- Ensure all titles stated in the table of contents are covered in the documentation with their description
- Ensure each section has its logical conclusion

### Requirement 4: Code Reference Requirements
- When referencing code snippets, use this format for file paths: `[<file_path_from_github>/<code_content>:L<start>-<end>](<file_path_from_github>/<code_content>:L<start>-<end>)` with coordinates of code lines in codebase
- Ensure all code references are accurate, traceable, and directly relevant

### Requirement 5: Contextual Integration
- Maintain logical flow ensuring readers understand section's position and significance
- Provide context showing how this section relates to overall documentation structure

### Requirement 6: Evidence-Based Documentation
- For each key conclusion or description, indicate which files' analysis led to it
- Ensure all claims are supported by actual code analysis

### Requirement 7: Format Compliance
- Ensure output section numbering is sequential
- Format output exclusively in markdown
- Maintain consistency with overall documentation style

### Requirement 8: Code Examples
- Ensure the subsection includes practical code examples to demonstrate use cases.
- Ensure each code snippet has clear text with purpose explanation.

### Requirement 9: Module Template Enforcement
- If the `{section_path}` indicates a module or component documentation chapter, you must use standardized H2 headings corresponding to the Module Template.
- Do not merge these headings or alter their names. This ensures consistent navigation across the entire documentation set.
- If information for a specific template section is absent in the code, do not omit the heading; instead, don't generate it.

**Strict Adherence Rules:**

### Rule 1: Information Sufficiency Check
- If information is insufficient to cover section requirements, do not generate content
- **Prohibition:** Do not fabricate information to compensate for insufficient data

### Rule 2: Strict Source Constraint
- **Mandatory:** Content generation must be strictly based on provided tree-sitter invocation results and code insights
- **Prohibition:** Do not make unfounded speculations or add external knowledge not present in the provided context

### Rule 3: Comprehensive Revision Principle
- **Prohibition:** Do not force associations or fabricate information when tree-sitter results are limited
- **Quality Standard:** Choose not to generate results rather than produce inaccurate content

### Rule 4: Authentic Representation Requirement
- **Mandatory:** Flowcharts must be realistic representations of actual system behavior
- **Prohibition:** Do not add fictional features or modules to enhance document completeness

### Rule 5: Quantitative Accuracy Imperative
- **Prohibition:** Do not fabricate any quantitative numerical information, file paths, code ranges, or similar data
- **Quality Standard:** Verify all numerical data against actual source code before inclusion

**Output Format Requirement:**
- Output content directly in markdown format without additional explanations
- Ensure all code snippets have appropriate syntax highlighting
- Maintain professional formatting and presentation standards

---

## Output Destination

Save generated documentation to:
`{{repository_name}}/.opencode/generated_document.md`

---
