"""Expose original helper functions over MCP stdio; never implement scoring here."""
import argparse
import contextlib
import importlib.util
import inspect
import json
from pathlib import Path
import sys

MODULES = {
    'utils': ('code_summarizer', 'utils.py', ('get_repository_structure',)),
    'verifier_utils': ('md_verifier', 'verifier_utils.py', ('codebase_to_blocks', 'calculate_coverage_adjusted_fidelity', 'calculate_correct_verdicts_ratio', 'calculate_f_quality_score')),
    'md_quality_metrics': ('dus', 'md_quality_metrics.py', ('get_total_info',)),
    'metrics': ('doc_gen', 'metrics.py', ('calculate_composite_score',)),
}
INSTALLED = {'code_summarizer': 'code-summarizer', 'md_verifier': 'md-verifier', 'dus': 'evaluate-dus', 'doc_gen': 'md-doc-gen'}


def load_functions(root, namespace):
    sys.dont_write_bytecode = True
    folder, filename, names = MODULES[namespace]
    path = root / folder / filename
    if not path.is_file():
        path = root / INSTALLED[folder] / filename
    spec = importlib.util.spec_from_file_location('_original_' + namespace, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    with contextlib.redirect_stdout(sys.stderr):
        spec.loader.exec_module(module)
    return {name: getattr(module, name) for name in names}


def schema(function):
    properties, required = {}, []
    for name, param in inspect.signature(function).parameters.items():
        if name in ('verdicts',):
            field = {'type': 'array', 'items': {'type': 'object'}}
        elif name in ('titles', 'texts', 'paragraphs', 'code_snippets', 'links', 'files', 'excluded_dirs', 'included_extensions'):
            field = {'type': 'array', 'items': {'type': 'string'}}
        elif name in ('max_workers', 'max_depth'):
            field = {'type': 'integer'}
        elif name in ('md_to_code', 'code_to_md', 'dus', 'beta', 'url_check_timeout'):
            field = {'type': 'number'}
        else:
            field = {'type': 'string'}
        if param.default is inspect.Parameter.empty:
            required.append(name)
        else:
            field['default'] = param.default
            if param.default is None:
                field['type'] = [field['type'], 'null']
        properties[name] = field
    return {'type': 'object', 'properties': properties, 'required': required, 'additionalProperties': False}


def respond(request, functions, namespace):
    if 'id' not in request:
        return None
    reply = {'jsonrpc': '2.0', 'id': request['id']}
    method, params = request.get('method'), request.get('params', {})
    if method == 'initialize':
        version = params.get('protocolVersion')
        reply['result'] = {'protocolVersion': version if version in ('2024-11-05', '2025-03-26', '2025-06-18') else '2024-11-05', 'capabilities': {'tools': {}}, 'serverInfo': {'name': 'original-' + namespace, 'version': '1.0.0'}}
    elif method == 'ping':
        reply['result'] = {}
    elif method == 'tools/list':
        reply['result'] = {'tools': [{'name': name, 'description': f'Original {namespace}.{name}. ' + (inspect.getdoc(fn) or ''), 'inputSchema': schema(fn)} for name, fn in functions.items()]}
    elif method == 'tools/call':
        name = params.get('name')
        if name not in functions:
            reply['error'] = {'code': -32602, 'message': 'Unknown tool'}
        else:
            try:
                arguments = params.get('arguments', {})
                inspect.signature(functions[name]).bind(**arguments)
                with contextlib.redirect_stdout(sys.stderr):
                    result = functions[name](**arguments)
                reply['result'] = {'content': [{'type': 'text', 'text': json.dumps(result, ensure_ascii=False, allow_nan=False)}]}
            except Exception as exc:
                reply['result'] = {'isError': True, 'content': [{'type': 'text', 'text': f'{type(exc).__name__}: {exc}'}]}
    else:
        reply['error'] = {'code': -32601, 'message': 'Method not found'}
    return reply


def install(workspace, python):
    """Register tools only. Do not alter skills, prompts or execution policy."""
    config_path = workspace / '.opencode/opencode.json'
    config = json.loads(config_path.read_text())
    adapter_path = workspace / '.opencode/original_tools_mcp.py'
    adapter_path.write_bytes(Path(__file__).read_bytes())
    servers = config.setdefault('mcp', {}).setdefault('servers', {})
    for namespace in MODULES:
        servers[namespace] = {'type': 'local', 'command': [str(python), str(adapter_path.resolve()), '--skills-root', str(workspace / '.opencode/skills'), '--namespace', namespace], 'codemode': False}
    config_path.write_text(json.dumps(config, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--skills-root', type=Path, required=True)
    parser.add_argument('--namespace', choices=MODULES, required=True)
    args = parser.parse_args()
    functions = load_functions(args.skills_root, args.namespace)
    for line in sys.stdin:
        try:
            request = json.loads(line)
            if not isinstance(request, dict) or request.get('jsonrpc') != '2.0':
                reply = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32600, 'message': 'Invalid request'}}
            else:
                reply = respond(request, functions, args.namespace)
        except json.JSONDecodeError:
            reply = {'jsonrpc': '2.0', 'id': None, 'error': {'code': -32700, 'message': 'Parse error'}}
        if reply is not None:
            print(json.dumps(reply, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
