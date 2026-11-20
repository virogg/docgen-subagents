import bisect
import itertools
import string
import os
import re
import ipaddress


import functools
from typing import List, Dict, Any, Iterable, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed, TimeoutError as FuturesTimeoutError
from dataclasses import dataclass, field
from collections import defaultdict
import urllib3
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ═══════════════════════════════════════════════════════════════
# MEMORY-EFFICIENT AGGREGATION
# ═══════════════════════════════════════════════════════════════
@dataclass
class CodeErrorStats:
    """Memory-efficient accumulator for code error statistics."""
    total_syntax_errors: int = 0
    total_codestyle_errors: int = 0
    snippets_with_syntax_errors: int = 0
    snippets_with_codestyle_errors: int = 0
    num_snippets: int = 0
    
    def accumulate(self, snippet_stats: Dict[str, Any]) -> None:
        """Single-pass accumulation - no intermediate lists needed."""
        self.num_snippets += 1
        self.total_syntax_errors += snippet_stats.get('syntax_error_count', 0)
        self.total_codestyle_errors += snippet_stats.get('codestyle_error_count', 0)
        if snippet_stats.get('has_syntax_errors', False):
            self.snippets_with_syntax_errors += 1
        if snippet_stats.get('has_codestyle_errors', False):
            self.snippets_with_codestyle_errors += 1
    
    def to_dict(self) -> Dict[str, Any]:
        n = self.num_snippets
        return {
            'total_syntax_errors': self.total_syntax_errors,
            'total_codestyle_errors': self.total_codestyle_errors,
            'total_errors': self.total_syntax_errors + self.total_codestyle_errors,
            'snippets_with_syntax_errors': self.snippets_with_syntax_errors,
            'snippets_with_codestyle_errors': self.snippets_with_codestyle_errors,
            'syntax_error_rate': self.snippets_with_syntax_errors / n if n else 0.0,
            'codestyle_error_rate': self.snippets_with_codestyle_errors / n if n else 0.0
        }


@dataclass
class CodeErrorResult:
    """
    Analyzes a Java code snippet for errors.
    
    Args:
        code_snippet (str): Java code snippet to analyze.
        
    Returns:
        dict: Error analysis containing:
            - 'errors': List of detailed error objects
            - 'error_count': Total number of errors found
            - 'error_types': Dict with count per error type
            - 'has_syntax_errors': Boolean - True if any syntax errors
            - 'has_codestyle_errors': Boolean - True if any codestyle errors
            - 'syntax_error_count': Number of syntax errors
            - 'codestyle_error_count': Number of codestyle errors
    """
    errors: List[Dict] = field(default_factory=list)
    
    @property
    def error_count(self) -> int:
        return len(self.errors)
    
    @property
    def syntax_errors(self) -> List[Dict]:
        return [e for e in self.errors if e['type'] == 'syntax']
    
    @property
    def codestyle_errors(self) -> List[Dict]:
        return [e for e in self.errors if e['type'] == 'codestyle']
    
    @property
    def has_syntax_errors(self) -> bool:
        return any(e['type'] == 'syntax' for e in self.errors)
    
    @property
    def has_codestyle_errors(self) -> bool:
        return any(e['type'] == 'codestyle' for e in self.errors)
    
    @property
    def error_rules(self) -> Set[str]:
        return {e['rule'] for e in self.errors}
    
    @property
    def error_types_count(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for e in self.errors:
            counts[e['type']] = counts.get(e['type'], 0) + 1
        return counts
    
    def to_summary_dict(self) -> dict:
        return {
            'error_count': self.error_count,
            'has_syntax_errors': self.has_syntax_errors,
            'has_codestyle_errors': self.has_codestyle_errors,
            'syntax_error_count': len(self.syntax_errors),
            'codestyle_error_count': len(self.codestyle_errors),
            'error_rules': list(self.error_rules)
        }
    
    def to_full_dict(self) -> dict:
        return {
            'errors': self.errors,
            'error_count': self.error_count,
            'error_types': self.error_types_count,
            'has_syntax_errors': self.has_syntax_errors,
            'has_codestyle_errors': self.has_codestyle_errors,
            'syntax_error_count': len(self.syntax_errors),
            'codestyle_error_count': len(self.codestyle_errors)
        }


# Suppress SSL warnings since we use verify=False to avoid corporate proxy issues
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


CODEBLOCK_PATTERN = re.compile(r'```([a-z_]+\n[^`]+?)```', re.I)
INVALID_NUMBER_FORMAT_PATTERN = re.compile(r'^\d+\s*\.\s*\d+\s*\.\s*', re.I)
INVALID_ANNOTATION_PATTERN = re.compile(r'@\w+(\(.*?\))?', re.I)


DEFAULT_URL = 'https://1.1.1.1/'
SOFT_URL_EXTRACTOR = re.compile(r'(?:https?://|www\.)[^\s<>"]+|[a-zA-Z0-9.-]+\.(?:[a-zA-Z]{2,63})\b(?:/[^\s<>"]*)?', re.I)
URL_STRUCTURE_REGEX = re.compile(r'^(?:https?://)?([a-z0-9.-]+)(?::\d+)?(?:/.*)?$', re.I)


# Pre-defined frozensets for O(1) lookups
_BLOCK_NODE_TYPES = frozenset({
    'class_declaration', 'method_declaration', 'if_statement',
    'for_statement', 'while_statement', 'do_statement',
    'try_statement', 'catch_clause', 'finally_clause',
    'switch_statement', 'lambda_expression'
})
_BRACKET_CHARS = frozenset('{}()[]')
_BRANCH_NODE_TYPES = frozenset({
    'if_statement', 'for_statement', 'enhanced_for_statement',
    'while_statement', 'do_statement', 'catch_clause',
    'conditional_expression', 'case_clause'
})
_CLASS_LIKE_PARENTS = frozenset({'class_declaration', 'enum_declaration'})
_LOGICAL_OPS = frozenset({'&&', '||'})
_PASCAL_CASE_TYPES = frozenset({'class_declaration', 'interface_declaration', 'enum_declaration'})
_PASCAL_CASE_RULES = {
    'class_declaration': ('CLASS_NAMING_CONVENTION', 'Class'),
    'interface_declaration': ('INTERFACE_NAMING_CONVENTION', 'Interface'),
    'enum_declaration': ('ENUM_NAMING_CONVENTION', 'Enum'),
}
_SKIP_CHILD_TYPES = frozenset({';', 'whitespace', 'line_comment', 'block_comment'})
_VARIABLE_DECL_TYPES = frozenset({'local_variable_declaration', 'field_declaration'})


IGNORE_TOKEN_TYPES = frozenset({'whitespace', 'line_comment', 'block_comment'})


# Pre-defined at module level to avoid recreating on each call
_HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
_STATUS_OK = frozenset({200, 204})


# Pre-calculated byte offsets for wrapper injections to avoid str.index()
_METHOD_WRAPPER_PREFIX = b"class __Dummy__ { Object __m__() { "
_CLASS_WRAPPER_PREFIX = b"class __Dummy__ { "


# ═══════════════════════════════════════════════════════════════
# LAZY-LOADED HEAVY DEPENDENCIES (saves ~500ms-2s startup time)
# ═══════════════════════════════════════════════════════════════
_nlp = None
_parser = None
_DIC = None

def _get_spacy_nlp():
    """Lazy-load spaCy with minimal pipeline for fast tokenization.
    
    Uses blank English model + sentencizer:
    - No model download required (unlike en_core_web_sm)
    - Rule-based tokenizer identical to full models
    - Rule-based sentence boundary detection
    - ~50ms load time vs ~200-500ms for full model
    """
    global _nlp
    if _nlp is None:
        import spacy
        _nlp = spacy.blank("en")
        _nlp.add_pipe('sentencizer')
    return _nlp


def _get_dic():
    global _DIC
    if _DIC is None:
        import pyphen
        _DIC = pyphen.Pyphen(lang='en_US')
    return _DIC


def _get_parser():
    """Lazy-load Tree-sitter to avoid startup penalty."""
    global _parser
    if _parser is None:
        import tree_sitter_java as tsjava
        from tree_sitter import Language, Parser
        _parser = Parser(Language(tsjava.language()))
    return _parser


# ═══════════════════════════════════════════════════════════════
# CONNECTION POOL (reuse connections, ~3x faster for many URLs)
# ═══════════════════════════════════════════════════════════════
_session: Optional[requests.Session] = None

def _get_session() -> requests.Session:
    """Get or create a session with connection pooling and retries."""
    global _session
    if _session is None:
        _session = requests.Session()
        _session.headers.update(_HEADERS)
        _session.verify = False
        
        # Configure connection pooling
        adapter = HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=Retry(
                total=1,
                backoff_factor=0.1,
                allowed_methods={'HEAD'},
                raise_on_status=False
            )
        )
        _session.mount('http://', adapter)
        _session.mount('https://', adapter)
    return _session


# ═══════════════════════════════════════════════════════════════
# URL CHECKING (OPTIMIZED)
# ═══════════════════════════════════════════════════════════════
@functools.lru_cache(maxsize=512)
def _check_url_cached(url: str) -> bool:
    """Check URL with caching. Thread-safe due to GIL on cache access."""
    try:
        session = _get_session()
        response = session.head(
            url,
            allow_redirects=True,
            timeout=4,  # Reduced from 15s to 4s
        )
        return response.status_code in _STATUS_OK
    except requests.exceptions.RequestException:
        return False


def is_network_available():
    try:
        response = requests.get(DEFAULT_URL, timeout=3)
        return True
    except requests.ConnectionError:
        return False
    

def _extract_urls(text: str) -> list:
    """Extract all candidates to URL."""
    return SOFT_URL_EXTRACTOR.findall(text)


def _has_errors(node) -> bool:
    """
    Iteratively checks if an AST node contains any ERROR nodes.
    Converted from recursion to prevent RecursionError and speed up execution.
    """
    stack = [node]
    while stack:
        n = stack.pop()
        if n.type == 'ERROR':
            return True
        if n.children:
            stack.extend(n.children)
    return False


def _get_parse_context(code: str):
    """
    Attempts to parse the code. If it fails due to missing class/method wrappers,
    it dynamically injects dummy wrappers and calculates the byte offsets 
    so we can isolate the original code later.

    Args:
        code (str): Code snippet.

    Returns:
        tree_sitter.Tree: tree for given code.
        int: start offset.
        int: end offset.
    """
    original_code = code.strip()
    if not original_code:
        return _get_parser().parse(b""), 0, 0

    original_bytes = original_code.encode('utf8')
    parser = _get_parser()
    end_offset = len(original_bytes)

    # Attempt 1: Parse raw code
    tree = parser.parse(original_bytes)
    if not _has_errors(tree.root_node):
        return tree, 0, end_offset

    # Attempt 2: Wrap in a dummy method
    wrapped_method_bytes = _METHOD_WRAPPER_PREFIX + original_bytes + b" } }"
    tree_method = parser.parse(wrapped_method_bytes)
    if not _has_errors(tree_method.root_node):
        start_offset = len(_METHOD_WRAPPER_PREFIX)
        return tree_method, start_offset, start_offset + end_offset

    # Attempt 3: Wrap in a dummy class
    wrapped_class_bytes = _CLASS_WRAPPER_PREFIX + original_bytes + b" }"
    tree_class = parser.parse(wrapped_class_bytes)
    start_offset = len(_CLASS_WRAPPER_PREFIX)

    return tree_class, start_offset, start_offset + end_offset


def _calculate_cyclomatic_complexity(code: str) -> int:
    """
    Calculates Cyclomatic Complexity for both full files and non-normalized snippets.

    Args:
        code (str): Code snippet.

    Returns:
        int: number that means code difficulty for understanding.
    """
    tree, start_byte, end_byte = _get_parse_context(code)
    complexity = 1

    stack = [tree.root_node]
    start = start_byte
    end = end_byte

    while stack:
        node = stack.pop()
        n_start = node.start_byte
        n_end = node.end_byte

        # Check if node is strictly within our target bounds
        if start <= n_start and n_end <= end:
            n_type = node.type
            if n_type in _BRANCH_NODE_TYPES:
                complexity += 1
            elif n_type == 'binary_expression':
                # Inline check for logical operators
                for child in node.children:
                    if child.type in _LOGICAL_OPS:
                        complexity += 1
                        break

        # Prune branches that are completely outside our target window
        for child in node.children:
            if child.end_byte > start and child.start_byte < end:
                stack.append(child)

    return complexity


def _tokenize_code(code: str, include_whitespace: bool = False) -> list[str]:
    """
    Tokenizes code, automatically compensating for missing structural wrappers.

    Args:
        code (str): Code snippet.
        include_whitespace (bool): incluse whitespace to tokens set or not.

    Returns:
        list(str): list with tokens.
    """
    tree, start_byte, end_byte = _get_parse_context(code)
    tokens = []
    
    stack = [tree.root_node]
    ignore_types = frozenset() if include_whitespace else IGNORE_TOKEN_TYPES
    start = start_byte
    end = end_byte
    decode_utf8 = bytes.decode

    while stack:
        node = stack.pop()
        
        if not node.children:
            n_start = node.start_byte
            n_end = node.end_byte
            
            if start <= n_start and n_end <= end:
                if node.type not in ignore_types:
                    tokens.append(decode_utf8(node.text))
        else:
            for child in node.children:
                if child.end_byte > start and child.start_byte < end:
                    stack.append(child)

    return tokens


def _count_lines(text: str) -> int:
    """Count lines without creating a list."""
    if not text:
        return 0
    return text.count('\n') + 1


def _count_tokens(code_snippet):
    return len(_tokenize_code(code_snippet))


def _separate_text_and_code(md_content: str):
    """Generator for memory-efficient text/code separation."""
    last_end = 0

    for match in CODEBLOCK_PATTERN.finditer(md_content):
        start, end = match.span()

        text_part = md_content[last_end:start]
        if text_part.strip():
            yield ("text", text_part)

        yield ("code", match.group(1))
        last_end = end

    remaining_text = md_content[last_end:]
    if remaining_text.strip():
        yield ("text", remaining_text)


def get_lines_count_text_vs_code(text):
    """
    Return the information about lines count of text and code snippet within paragraph.

    Args:
        text str:Text block.

    Returns:
        dict: JSON answer.
    """

    separated = _separate_text_and_code(text)
    l_code = sum(_count_lines(p) for p in separated if p[0] == 'code')
    l_text = sum(_count_lines(p) for p in separated if p[0] == 'text')
    
    denom = l_code + l_text if l_code > 0 or l_text > 0 else 0
    return {
        'ratio': 1 if denom == 0 else l_code / denom
    }


def get_title_info(title: str) -> dict:
    """
    Generate the information about current title, including title length in tokens.

    Args:
        title (str): Title text.

    Returns:
        dict: JSON answer with token count.
    """
    nlp = _get_spacy_nlp()
    doc = nlp(title)
    
    return {
        'title_length': len(doc)
    }


def flesch_reading_ease(doc) -> float:
    """
    Calculates Flesch Reading Ease score for sentences extracted with spacy.

    Args:
        doc (iterable): SpaCy document with information about sentences and tokens.

    Returns:
        float: value of score; if it is greater, then the text is easier for reading.
    """
    words = [token.text for token in doc if token.is_alpha]
    if not words:
        return 0.0

    syllable_count = sum(
        len(_get_dic().inserted(w).split('-')) 
        for w in words
    )

    return (
        206.835 
        - 1.015 * (len(words) / len(list(doc.sents))) 
        - 84.6 * (syllable_count / len(words))
    )


def get_paragraph_info(text: str) -> dict:
    """
    Generate information about current text segment: Flesch Reading Ease score,
    average sentence length, count of too long/short sentences.

    Args:
        text (str): Text segment.

    Returns:
        dict: JSON answer with readability metrics.
    """
    nlp = _get_spacy_nlp()
    doc = nlp(text)
    sentences = list(doc.sents)
    
    if not sentences:
        return {
            'paragraph_flesch_reading_ease': 0.0,
            'avg_sentences_len': 0.0,
            'sentences_count': 0,
            'count_of_long_sents': 0,
            'count_of_short_sents': 0
        }
    
    # Single-pass: tokens already computed during nlp(text)
    total_words = 0
    too_long = 0
    too_short = 0
    
    for sent in sentences:
        wc = len(sent)
        total_words += wc
        if wc > 35:
            too_long += 1
        elif wc < 5:
            too_short += 1
    
    return {
        'paragraph_flesch_reading_ease': flesch_reading_ease(doc),
        'avg_sentences_len': total_words / len(sentences),
        'sentences_count': len(sentences),
        'count_of_long_sents': too_long,
        'count_of_short_sents': too_short
    }


def _is_valid_url_offline(url: str) -> bool:
    try:
        url_clean = url.strip().rstrip('.,;:!?')
        match = URL_STRUCTURE_REGEX.match(url_clean)
        if not match: 
            return False
        
        host = match.group(1).lower()
        if host.endswith('.'): 
            host = host[:-1]

        # IP address validation
        try:
            ipaddress.ip_address(host)
            return True
        except ValueError:
            pass

        # localhost or TLD-structures validation
        if '.' not in host:
            return host == 'localhost'
            
        parts = host.split('.')
        tld = parts[-1]
        
        # TLD length from 2 to 63 symbols, contains only digits, latin characters and dash
        if not tld or not re.match(r'^[a-z0-9-]+$', tld) or not (2 <= len(tld) <= 63):
            return False
            
        # Protection from double dots (i.e. google..com)
        if any(not part for part in parts):
            return False
            
        return True
    except Exception:
        return False
        

def calculate_correct_links_offline(url_list: Iterable[str], max_urls_to_check: int = 100) -> float:
    """
    Obtain the percentage of web URLs without access to network.

    Args:
        url_list (iterable): Any container with extracted URLs.
        max_urls_to_check (int): Limit for set size.

    Returns:
        float: Percentage of correct links.
    """
    if not url_list:
        return 0.0

    seen: Set[str] = set()
    correct_count = 0
    checked_count = 0
    
    for text in url_list:
        for url in _extract_urls(text): 
            if url not in seen:
                seen.add(url)
                checked_count += 1
                
                if _is_valid_url_offline(url):
                    correct_count += 1
                
                if checked_count >= max_urls_to_check:
                    break
        if checked_count >= max_urls_to_check:
            break

    return correct_count / checked_count if checked_count else 0.0


def calculate_correct_links(
    url_list: Iterable[str],
    max_workers: int = 15,
    per_url_timeout: float = 4.0,
    total_timeout: float = 30.0,  # Overall timeout
    max_urls_to_check: int = 100,  # Limit to prevent runaway checks
    offline_penalty: float = 0.80 # Penalty of correctness' percent if network is not available
) -> float:
    """
    Obtain the percentage of live, reachable web URLs. Ignores local filepaths automatically.

    Args:
        url_list (iterable): Any container with extracted URLs.
        max_workers (int): Maximum concurrent requests (default: 10).

    Returns:
        float: Percentage of correct links.
        bool: Status if network is available.
    """
    if not is_network_available():
        return calculate_correct_links_offline(url_list) * offline_penalty, False

    status = True
    
    if not url_list:
        return 0.0, status

    # Extract and deduplicate URLs (single pass, no intermediate lists)
    seen: Set[str] = set()
    unique_urls: List[str] = []
    
    for text in url_list:
        for url in _extract_urls(text):
            if url not in seen:
                seen.add(url)
                unique_urls.append(url)
                if len(unique_urls) >= max_urls_to_check:
                    break
        if len(unique_urls) >= max_urls_to_check:
            break

    if not unique_urls:
        return 0.0, status

    # Use as_completed for early termination on timeout
    correct_count = 0
    checked_count = 0
    
    try:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_url = {
                executor.submit(_check_url_cached, url): url 
                for url in unique_urls
            }
            
            for future in as_completed(future_to_url, timeout=total_timeout):
                if future.result():
                    correct_count += 1
                checked_count += 1
                
    except FuturesTimeoutError:
        # Return partial result instead of failing
        pass

    return correct_count / checked_count if checked_count else 0.0, status


# Module-level cache for file indices (safe for concurrent reads)
_file_index_cache: dict[str, dict] = {}


def _build_file_index(repo_path: str) -> dict[str, set]:
    """Build a suffix index for O(1) file path lookup.
    
    For file 'a/b/c/d.txt', indexes all suffixes:
    'd.txt', 'c/d.txt', 'b/c/d.txt', 'a/b/c/d.txt'
    
    This replicates glob('**/{path}') behavior with O(1) lookup.
    """
    suffix_index: dict[str, set] = {}
    
    for root, _, files in os.walk(repo_path):
        for f in files:
            rel_path = os.path.relpath(os.path.join(root, f), repo_path).replace('\\', '/')
            parts = rel_path.split('/')
            
            for i in range(len(parts)):
                suffix = '/'.join(parts[i:])
                if suffix in suffix_index:
                    suffix_index[suffix].add(rel_path)
                else:
                    suffix_index[suffix] = {rel_path}
    
    return suffix_index


def clear_file_index_cache(repo_path: str = None):
    """Clear cached file index for one or all repos."""
    if repo_path:
        _file_index_cache.pop(repo_path, None)
    else:
        _file_index_cache.clear()


def calculate_correct_filepaths(repo_path: str, files_list) -> float:
    """
    Obtain percent of generated filenames that actually exist in the repository.

    Args:
        repo_path (str): root path of a repository project.
        files_list (iterable str): container with extracted file paths.

    Returns:
        float: percent of correct paths.
    """
    if not files_list:
        return 0.0

    # Build or retrieve cached file index
    if repo_path not in _file_index_cache:
        _file_index_cache[repo_path] = _build_file_index(repo_path)
    suffix_index = _file_index_cache[repo_path]

    # Count matches with normalized paths
    valid_count = 0
    for p in files_list:
        normalized = p.replace('\\', '/').lstrip('/')
        if normalized in suffix_index:
            valid_count += 1

    perc = valid_count / len(files_list)
    clear_file_index_cache(repo_path)
    return perc


def _describe_syntax_error(error_text: str, full_code: str) -> str:
    """
    Attempts to provide a human-readable description of a syntax error.
    
    Args:
        error_text: The text that caused the syntax error
        full_code: The full code snippet for context
        
    Returns:
        str: Description of the likely error
    """
    error_text = error_text.strip()
    
    if not error_text:
        return "Unexpected end of input"
    
    bracket_pairs = [('(', ')', 'parenthesis'), ('{', '}', 'brace'), ('[', ']', 'bracket')]
    for open_b, close_b, name in bracket_pairs:
        open_count = error_text.count(open_b)
        close_count = error_text.count(close_b)
        if open_count > close_count:
            return f"Unclosed {name}"
        elif close_count > open_count:
            return f"Unexpected closing {name}"
    
    if INVALID_NUMBER_FORMAT_PATTERN.match(error_text):
        return "Invalid number format (multiple decimal points)"
    
    if '@' in error_text and not INVALID_ANNOTATION_PATTERN.search(error_text):
        return "Invalid annotation syntax"
    
    if re.match(r'^[;,\.:]+$', error_text):
        return f"Unexpected token: '{error_text}'"
    
    if re.search(r'\w\s+\w\s*\(', error_text) and not any(kw in error_text for kw in ('if', 'for', 'while', 'switch', 'catch', 'new')):
        return "Possible missing operator or semicolon"
    
    display_text = error_text[:50] + '...' if len(error_text) > 50 else error_text
    return f"Syntax error near: '{display_text}'"


def _check_naming_conventions(code: str, tree, start_byte: int, end_byte: int, pos_converter) -> list[dict]:
    """
    Checks Java naming conventions using AST.
    
    Rules checked:
    - Classes/Interfaces/Enums: PascalCase
    - Methods: camelCase
    - Constants (static final): UPPER_SNAKE_CASE
    - Regular variables: camelCase
    """
    errors = []
    stack = [tree.root_node]

    while stack:
        node = stack.pop()
        node_type = node.type

        # Skip nodes entirely outside our range
        if node.end_byte <= start_byte or node.start_byte >= end_byte:
            continue

        # Full containment check for naming rules
        in_bounds = node.start_byte >= start_byte and node.end_byte <= end_byte

        if in_bounds:
            # PascalCase checks (class, interface, enum) - consolidated
            if node_type in _PASCAL_CASE_TYPES:
                rule, entity_type = _PASCAL_CASE_RULES[node_type]
                for child in node.children:
                    if child.type == 'identifier':
                        name = child.text.decode('utf8')
                        if name and not name[0].isupper():
                            line, col = pos_converter(child.start_byte)
                            errors.append({
                                'type': 'codestyle',
                                'message': f"{entity_type} name '{name}' should be in PascalCase",
                                'line': line,
                                'column': col,
                                'snippet': name,
                                'rule': rule
                            })
                        break

            # Method naming check
            elif node_type == 'method_declaration':
                for child in node.children:
                    if child.type != 'identifier':
                        continue
                    name = child.text.decode('utf8')
                    if not name:
                        break

                    # Constructor detection
                    parent = node.parent
                    is_constructor = False
                    if parent and parent.type in _CLASS_LIKE_PARENTS:
                        for sibling in parent.children:
                            if sibling.type == 'identifier':
                                is_constructor = sibling.text.decode('utf8') == name
                                break

                    if not is_constructor and (name[0].isupper() or ('_' in name and name != name.lower())):
                        line, col = pos_converter(child.start_byte)
                        errors.append({
                            'type': 'codestyle',
                            'message': f"Method name '{name}' should be in camelCase",
                            'line': line,
                            'column': col,
                            'snippet': name,
                            'rule': 'METHOD_NAMING_CONVENTION'
                        })
                    break

            # Variable/field naming check
            elif node_type in _VARIABLE_DECL_TYPES:
                is_constant = False
                for child in node.children:
                    if child.type == 'modifiers':
                        mods_text = child.text.decode('utf8')
                        is_constant = 'static' in mods_text and 'final' in mods_text
                        break

                for child in node.children:
                    if child.type != 'variable_declarator':
                        continue
                    for subchild in child.children:
                        if subchild.type != 'identifier':
                            continue
                        name = subchild.text.decode('utf8')
                        if not name:
                            break

                        line, col = pos_converter(subchild.start_byte)

                        if is_constant:
                            if name != name.upper() or '-' in name or ' ' in name:
                                errors.append({
                                    'type': 'codestyle',
                                    'message': f"Constant '{name}' should be in UPPER_SNAKE_CASE",
                                    'line': line,
                                    'column': col,
                                    'snippet': name,
                                    'rule': 'CONSTANT_NAMING_CONVENTION'
                                })
                        elif name[0].isupper():
                            errors.append({
                                'type': 'codestyle',
                                'message': f"Variable name '{name}' should be in camelCase",
                                'line': line,
                                'column': col,
                                'snippet': name,
                                'rule': 'VARIABLE_NAMING_CONVENTION'
                            })
                        break

        # Add overlapping children to stack
        for child in node.children:
            if child.end_byte > start_byte and child.start_byte < end_byte:
                stack.append(child)

    return errors


def _check_indentation_consistency(code: str) -> list[dict]:
    """
    Checks for inconsistent indentation in code.
    
    Detects:
    - Mixed tabs and spaces
    - Inconsistent indentation width (for space-based indentation)
    """
    errors = []
    lines = code.split('\n')
    
    has_tabs = False
    has_spaces = False
    space_indent_widths = set()
    first_line_with_tabs = 0
    first_line_with_spaces = 0
    
    for i, line in enumerate(lines, 1):
        stripped = line.lstrip()
        if not stripped:
            continue
        
        # Fast comment detection - single slice + comparisons
        first_two = stripped[:2]
        if first_two == '//' or first_two == '/*' or stripped[0] == '*':
            continue
        
        # Check indentation (line is guaranteed non-empty here)
        if line[0] == '\t':
            has_tabs = True
            if not first_line_with_tabs:
                first_line_with_tabs = i
            space_indent_widths.add((len(line) - len(line.lstrip('\t'))) * 4)
        elif line[0] == ' ':
            has_spaces = True
            if not first_line_with_spaces:
                first_line_with_spaces = i
            # Reuse stripped instead of calling lstrip(' ') again
            indent = len(line) - len(stripped)
            if indent > 0:
                space_indent_widths.add(indent)
    
    if has_tabs and has_spaces:
        errors.append({
            'type': 'codestyle',
            'message': "Mixed tabs and spaces for indentation",
            'line': min(first_line_with_tabs or 1, first_line_with_spaces or 1),
            'column': 1,
            'snippet': "",
            'rule': 'MIXED_INDENTATION'
        })
    
    if len(space_indent_widths) > 3:
        widths_str = ', '.join(sorted(str(w) for w in space_indent_widths if w > 0))
        errors.append({
            'type': 'codestyle',
            'message': f"Inconsistent indentation widths detected: [{widths_str}]",
            'line': 1,
            'column': 1,
            'snippet': "",
            'rule': 'INCONSISTENT_INDENTATION'
        })
    
    return errors


def _check_line_length(code: str, max_length: int = 120) -> list[dict]:
    """
    Checks for lines exceeding maximum length.
    
    Args:
        code: The code snippet to check
        max_length: Maximum allowed line length (default 120)
        
    Returns:
        List of error dicts for lines that are too long
    """
    errors = []
    lines = code.split('\n')
    
    for i, line in enumerate(lines, 1):
        if len(line) > max_length:
            # Extract a snippet around the limit for context
            start = max(0, max_length - 20)
            end = min(len(line), max_length + 20)
            snippet = line[start:end]
            if start > 0:
                snippet = '...' + snippet
            if end < len(line):
                snippet = snippet + '...'
            
            errors.append({
                'type': 'codestyle',
                'message': f"Line too long ({len(line)} characters, max {max_length})",
                'line': i,
                'column': max_length + 1,
                'snippet': snippet,
                'rule': 'MAX_LINE_LENGTH'
            })
    
    return errors


def _check_missing_semicolons(code: str, tree, start_byte: int, end_byte: int, pos_converter) -> list[dict]:
    """
    Attempts to detect statements that might be missing semicolons.
    Uses heuristics based on AST structure.
    """
    errors = []
    stack = [tree.root_node]

    while stack:
        node = stack.pop()
        node_type = node.type

        if node_type == 'expression_statement' and start_byte <= node.start_byte and node.end_byte <= end_byte:

            # Find last non-trivial child
            last_child = None
            for child in node.children:
                if child.type not in _SKIP_CHILD_TYPES:
                    last_child = child

            # Check if it looks like a missing semicolon
            if last_child and last_child.type == 'ERROR':
                error_text = last_child.text.decode('utf8').strip()
                # Heuristic: short error without brackets
                if len(error_text) < 20 and not any(c in _BRACKET_CHARS for c in error_text):
                    line, col = pos_converter(last_child.end_byte - 1)
                    errors.append({
                        'type': 'syntax',
                        'message': "Possible missing semicolon",
                        'line': line,
                        'column': col,
                        'snippet': error_text,
                        'rule': 'MISSING_SEMICOLON'
                    })

        # Add children that overlap with our range
        for child in node.children:
            if child.end_byte > start_byte and child.start_byte < end_byte:
                stack.append(child)

    return errors


def _check_unclosed_braces(code: str, tree, start_byte: int, end_byte: int, pos_converter) -> list[dict]:
    """
    Checks for unclosed braces by analyzing the AST structure.
    """
    errors = []
    stack = [tree.root_node]

    while stack:
        node = stack.pop()
        node_type = node.type

        if node_type in _BLOCK_NODE_TYPES:
            for child in node.children:
                if (child.type == 'ERROR' and
                    start_byte <= child.start_byte and
                    child.end_byte <= end_byte):
                    error_text = child.text.decode('utf8')
                    if '{' in error_text and '}' not in error_text:
                        line, col = pos_converter(child.start_byte)
                        errors.append({
                            'type': 'syntax',
                            'message': "Unclosed brace detected",
                            'line': line,
                            'column': col,
                            'snippet': error_text[:30],
                            'rule': 'UNCLOSED_BRACE'
                        })

        for child in node.children:
            if child.end_byte > start_byte and child.start_byte < end_byte:
                stack.append(child)

    return errors


def _extract_code_errors(code: str) -> list[dict]:
    """
    Extracts and categorizes errors from Java code snippets.
    
    Identifies:
    - Syntax errors (from tree-sitter ERROR nodes)
    - Codestyle errors (naming conventions, indentation, line length)
    - Structural issues (unclosed braces, missing semicolons)
    
    Args:
        code (str): Java code snippet.
        
    Returns:
        list[dict]: List of error objects, each containing:
            - 'type': Error category ('syntax', 'codestyle', 'structural')
            - 'message': Human-readable description of the error
            - 'line': Line number where error occurs (1-based)
            - 'column': Column number where error occurs (1-based)
            - 'snippet': The problematic code fragment
            - 'rule': Rule identifier for programmatic handling
    """
    errors = []
    original_code = code.strip()
    
    if not original_code:
        return errors
    
    tree, start_byte, end_byte = _get_parse_context(code)
    
    # Pre-compute line starts for O(log n) position lookup instead of O(n) per call
    line_starts = [0]
    for i, c in enumerate(original_code):
        if c == '\n':
            line_starts.append(i + 1)
    line_starts.append(len(original_code))  # Sentinel for boundary cases
    
    def byte_offset_to_position(byte_offset):
        original_offset = max(0, min(byte_offset - start_byte, len(original_code)))
        line_idx = bisect.bisect_right(line_starts, original_offset) - 1
        return line_idx + 1, original_offset - line_starts[line_idx] + 1
    
    # Iterative traversal with early pruning and syntax flag tracking
    has_syntax_errors = False
    stack = [tree.root_node]
    
    while stack:
        node = stack.pop()
        
        # Skip nodes entirely outside our range (prunes wrapper code)
        if node.end_byte <= start_byte or node.start_byte >= end_byte:
            continue
        
        if node.type == 'ERROR':
            has_syntax_errors = True
            error_text = node.text.decode('utf8')
            line, col = byte_offset_to_position(max(node.start_byte, start_byte))
            
            errors.append({
                'type': 'syntax',
                'message': _describe_syntax_error(error_text, original_code),
                'line': line,
                'column': col,
                'snippet': error_text[:50] + ('...' if len(error_text) > 50 else ''),
                'rule': 'SYNTAX_ERROR'
            })
        
        stack.extend(node.children)
    
    errors.extend(_check_naming_conventions(original_code, tree, start_byte, end_byte, byte_offset_to_position))
    errors.extend(_check_indentation_consistency(original_code))
    errors.extend(_check_line_length(original_code, max_length=120))
    
    if has_syntax_errors:
        errors.extend(_check_unclosed_braces(original_code, tree, start_byte, end_byte, byte_offset_to_position))
    
    errors.sort(key=lambda e: (e['line'], e['column']))
    return errors


def get_code_errors(code_snippet: str) -> dict:
    errors = _extract_code_errors(code_snippet)
    return CodeErrorResult(errors=errors)


def get_code_info(code_snippet):
    """
    Generate the information about current code fragment, including error analysis.
    
    Args:
        code_snippet (str): Code snippet.

    Returns:
        dict: JSON answer with code metrics and error summary.
    """
    result = get_code_errors(code_snippet)
    
    return {
        'lines_count': _count_lines(code_snippet),
        'tokens_count': _count_tokens(code_snippet),
        'cyclomatic_complexity': _calculate_cyclomatic_complexity(code_snippet),
        **result.to_summary_dict()  # Unpack summary directly
    }


# ═══════════════════════════════════════════════════════════════
# BATCH PROCESSOR (Memory-efficient parallel processing)
# ═══════════════════════════════════════════════════════════════
def _process_batch(func, items: List[Any], max_workers: int = 4) -> List[Any]:
    """Process items in parallel with bounded memory usage."""
    if not items:
        return []
    
    # For small batches, sequential is faster (no thread overhead)
    if len(items) < 10:
        return [func(item) for item in items]
    
    # For larger batches, use threads but with chunking
    results = [None] * len(items)
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {executor.submit(func, item): i for i, item in enumerate(items)}
        for future in as_completed(futures):
            idx = futures[future]
            results[idx] = future.result()
    
    return results


# ═══════════════════════════════════════════════════════════════
# MAIN ENTRY POINT (OPTIMIZED)
# ═══════════════════════════════════════════════════════════════
def get_total_info(
    repo_path: str,
    titles: List[str],
    texts: List[str],
    paragraphs: List[str],
    code_snippets: List[str],
    links: Iterable[str],
    files: Iterable[str],
    url_check_timeout: float = 30.0  # Configurable timeout
) -> Dict[str, Any]:
    """
    Generate linguistics information about paragraphs, titles and code fragments extracted from MD documentation.
    Also includes aggregated error statistics.

    Args:
        repo_path (str): path to repository
        titles list(str): List with titles.
        texts list(str): List with whole text blocks.
        paragraphs list(str): List with text blocks.
        code_snippets list(str): List with extracted code examples.
        links iterable(str): any container with extracted URLs.
        files iterable(str): container with extracted file paths.

    Returns:
        dict: JSON answer.
    """
    # Compute quick tasks sequentially if small, parallel if large
    titles_stats = _process_batch(get_title_info, titles)
    texts_stats = _process_batch(get_lines_count_text_vs_code, texts)
    paragraphs_stats = _process_batch(get_paragraph_info, paragraphs)
    
    # Code analysis is CPU-intensive - use separate pool
    code_snippets_stats = _process_batch(get_code_info, code_snippets, max_workers=4)
    
    # URL checking is I/O-bound - use dedicated pool with timeout
    correct_urls_percent, status = calculate_correct_links(
        links, 
        total_timeout=url_check_timeout
    )
    
    # File path checking (assuming similar pattern)
    correct_filepaths_percent = calculate_correct_filepaths(repo_path, files)
    
    # Single-pass aggregation (memory efficient)
    error_stats = CodeErrorStats()
    for snippet_stat in code_snippets_stats:
        error_stats.accumulate(snippet_stat)
    
    return {
        'titles_stats': titles_stats,
        'texts_stats': texts_stats,
        'paragraphs_stats': paragraphs_stats,
        'code_snippets_stats': code_snippets_stats,
        'correct_urls_percent': correct_urls_percent,
        'correct_filepaths_percent': correct_filepaths_percent,
        'network_available_status': status,
        'code_errors_summary': error_stats.to_dict()
    }


# ═══════════════════════════════════════════════════════════════
# CLEANUP (Call at program end)
# ═══════════════════════════════════════════════════════════════
def cleanup():
    """Close connection pool and clear caches."""
    global _session
    if _session:
        _session.close()
        _session = None
    _check_url_cached.cache_clear()
