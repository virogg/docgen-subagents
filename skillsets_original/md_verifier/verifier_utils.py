import os
import re
import json
import math

from collections import OrderedDict
from concurrent.futures import ThreadPoolExecutor


BETA = 0.75
CODEBLOCK_PATTERN = re.compile(r'```([a-z_]+\n[^`]+?)```', re.I)

# Pre-compiled at module level
_RE_FRONTMATTER = re.compile(r'^---[ \t]*\n.*?\n---[ \t]*\n?', re.DOTALL | re.MULTILINE)
_RE_CODE_BLOCKS = re.compile(r'```[a-zA-Z0-9_+\-]*\n[\s\S]*?```')
_RE_INLINE_CODE = re.compile(r'(?<!`)`([^`\n]+)`(?!`)')
_RE_HTML_TAGS = re.compile(r'<[^>]+>')

# Pre-compiled sets for O(1) lookups
EXCLUDED_DIRS = frozenset({'build', 'target', 'test', '.gradle', '.mvn'})
_PUBLIC_TYPES = frozenset({'class_declaration', 'interface_declaration', 'enum_declaration'})
_EXCLUDED_METHODS = frozenset({b'toString', b'hashCode', b'equals', b'getClass'})
_BEAN_PREFIXES = (b'get', b'set', b'is')
_TYPE_NAME_MAP = {
    'class_declaration': 'class',
    'interface_declaration': 'interface', 
    'enum_declaration': 'enum'
}

# First bytes for fast bean method exclusion
_BEAN_FIRST_BYTES = {b'g'[0], b's'[0], b'i'[0]}  # {103, 115, 105}


def _get_parser():
    """Create a new parser instance (thread-safe)."""
    import tree_sitter_java as tsjava
    from tree_sitter import Language, Parser
    return Parser(Language(tsjava.language()))

def _is_public(node):
    for child in node.children:
        if child.type == 'modifiers':
            return any(mod.type == 'public' for mod in child.children)
    return False

    
def _has_override(node):
    for child in node.children:
        if child.type == 'modifiers':
            for mod in child.children:
                if mod.type == 'marker_annotation':
                    return any(
                        ann.type == 'identifier' and ann.text == b'Override' 
                        for ann in mod.children
                    )
    return False

    
def _is_main_method(node) -> bool:
    """Check if method is public static void main(String[] args)."""
    name_node = node.child_by_field_name('name')
    if name_node is None or name_node.text != b'main':
        return False
    params_node = node.child_by_field_name('parameters')
    return params_node is not None and b'String' in params_node.text and b'args' in params_node.text


def _process_java_file(file_path: str, rel_path: str) -> list[dict]:
    """Parse a Java file and extract key blocks. Thread-safe."""
    with open(file_path, 'rb') as f:
        source_code = f.read()
    
    tree = _get_parser().parse(source_code)
    blocks = []
    append = blocks.append  # Local reference - avoids attribute lookup
    
    for child in tree.root_node.children:
        child_type = child.type
        
        # --- Public top-level types ---
        if child_type in _PUBLIC_TYPES:
            if child.parent.type != 'program':
                continue
            
            # Inline public check (avoids function call overhead)
            is_pub = False
            for c in child.children:
                if c.type == 'modifiers':
                    for m in c.children:
                        if m.type == 'public':
                            is_pub = True
                            break
                    break
            
            if is_pub:
                name_node = child.child_by_field_name('name')
                if name_node:
                    type_name = _TYPE_NAME_MAP[child_type]
                    append({
                        "type": type_name,
                        "name": name_node.text.decode('utf-8'),
                        "file": rel_path,
                        "key_indicator": f"public {type_name}"
                    })
            continue
        
        # --- Key methods (@Override or main) ---
        if child_type != 'method_declaration':
            continue
        
        name_node = child.child_by_field_name('name')
        if name_node is None:
            continue
        
        name_bytes = name_node.text
        
        # Fast exclusion: exact match or first-byte check
        if name_bytes in _EXCLUDED_METHODS:
            continue
        if name_bytes[0] in _BEAN_FIRST_BYTES and name_bytes.startswith(_BEAN_PREFIXES):
            continue
        
        # Inline @Override check
        is_override = False
        for c in child.children:
            if c.type == 'modifiers':
                for mod in c.children:
                    if mod.type == 'marker_annotation':
                        for ann in mod.children:
                            if ann.type == 'identifier' and ann.text == b'Override':
                                is_override = True
                                break
                        if is_override:
                            break
                break
        
        # Inline main check (only if not @Override)
        is_main = False
        if not is_override and name_bytes == b'main':
            params_node = child.child_by_field_name('parameters')
            if params_node is not None:
                params_text = params_node.text
                is_main = b'String' in params_text and b'args' in params_text
        
        if is_override or is_main:
            append({
                "type": "method",
                "name": name_bytes.decode('utf-8'),
                "file": rel_path,
                "key_indicator": "@Override" if is_override else "public static void main"
            })
    
    return blocks


def _process_file_task(args: tuple) -> tuple:
    """Unpack and process a single file task. Faster than lambda."""
    file_path, rel_path, pkg_name = args
    return pkg_name, _process_java_file(file_path, rel_path)


def codebase_to_blocks(repository_path: str, max_workers: int = 4) -> list[dict]:
    """Extracts key architectural Java blocks, grouped by package."""
    src_path = os.path.join(repository_path, 'src', 'main', 'java')
    if not os.path.exists(src_path):
        src_path = repository_path

    # Collect files with package info (single pass, minimal allocations)
    file_tasks = []
    sep = os.sep
    join = os.path.join  # Local reference
    relpath = os.path.relpath
    
    for dirpath, dirnames, filenames in os.walk(src_path):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        pkg_rel_path = relpath(dirpath, src_path)
        pkg_name = "default_package" if pkg_rel_path == '.' else pkg_rel_path.replace(sep, '.')
        
        for filename in filenames:
            if filename.endswith('.java'):
                file_path = join(dirpath, filename)
                file_tasks.append((file_path, relpath(file_path, repository_path), pkg_name))

    # Parse files in parallel
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = executor.map(_process_file_task, file_tasks)

    # Aggregate by package (preserves directory order)
    pkg_blocks = OrderedDict()
    for pkg_name, blocks in results:
        if blocks:
            if pkg_name in pkg_blocks:
                pkg_blocks[pkg_name].extend(blocks)
            else:
                pkg_blocks[pkg_name] = list(blocks)  # Copy to allow extension

    # Build final output
    final_output = []
    block_id = 1
    for pkg_id, (pkg_name, blocks) in enumerate(pkg_blocks.items(), 1):
        for block in blocks:
            block["block_id"] = f"B{block_id:03d}"
            block_id += 1
        
        final_output.append({
            "package_id": f"P{pkg_id:03d}",
            "package_name": pkg_name,
            "key_indicator": "package_directory",
            "info": blocks
        })

    return final_output


def _get_prose_word_count(md_text: str) -> int:
    """Count words in prose content, excluding code blocks and markup."""
    if not md_text:
        return 0
    
    text = md_text
    
    # Conditional substitutions - skip regex if pattern not present
    if text.startswith('---'):
        text = _RE_FRONTMATTER.sub(' ', text)
    
    if '```' in text:
        text = _RE_CODE_BLOCKS.sub(' ', text)
    
    if '`' in text:
        text = _RE_INLINE_CODE.sub(' ', text)
    
    if '<' in text:
        text = _RE_HTML_TAGS.sub(' ', text)
    
    return len(text.split())


def calculate_coverage_adjusted_fidelity(verdicts: list, md_doc_path: str) -> float:
    """
    Calculate accurately precision score for extracted claims, regardless of documentation size.

    Args:
        verdicts list(dict): each dict contains answer 'yes/no'.
        md_doc_path (str): string with path to technical documentation.

    Returns:
        float: result of formula.
    """
    if not verdicts:
        return 0.0
        
    # 1. Original Precision
    correct_verdicts = sum(1 for v in verdicts if v.get('answer') == 'yes')
    precision = correct_verdicts / len(verdicts)
    
    if precision == 0:
        return 0.0

    # 2.  Coverage Ratio (Did the LLM do its job?)
    with open(md_doc_path, 'r', encoding='utf-8') as f:
        md_content = f.read()
    
    md_word_count = _get_prose_word_count(md_content)
    # Density coefficient from FActScore paper (1 claim ~ 40 words)
    density_coeff = 0.025  
    expected_claims = max(5, round(md_word_count * density_coeff))
    actual_claims = len(verdicts)
    
    # 3. (Under-generation Penalty
    if actual_claims >= expected_claims:
        penalty = 1.0  # Greater or equal claims count
    else:
        ratio = actual_claims / expected_claims 
        penalty = math.exp(ratio - 1)  # Less facts
        
    fidelity_score = precision * penalty
    return round(fidelity_score, 5)


def calculate_correct_verdicts_ratio(verdicts):
    """
    Calculate ratio of correct verdicts.

    Args:
        verdicts (list(dict)): each dict contains answer 'yes/no'.

    Returns:
        float: result of formula.
    """
    return sum(1 for verdict in verdicts if verdict['answer'] == 'yes') / len(verdicts)


def calculate_f_quality_score(md_to_code, code_to_md, beta=BETA):
    """
    Calculate F-beta score for metrics.

    Args:
        md_to_code (float): precision, grounded truthness score.
        code_to_md (float): recall, document completeness score.

    Returns:
        float: result of formula.
    """
    return (1 + beta ** 2) * (md_to_code * code_to_md) / (beta ** 2 * md_to_code + code_to_md)
    