
### Courtesy of o1-preview (ChatGPT and Gemini failed on this)
### See pyparser-examples.txt for complex examples
### Some o1 attempts (failed and success) here https://platform.openai.com/playground/chat?preset=s3A0XxVSvFgJFbVXhSORn40k

import ast

def get_end_lineno(node):
    max_lineno = getattr(node, 'lineno', -1)
    for child in ast.iter_child_nodes(node):
        child_end_lineno = get_end_lineno(child)
        if child_end_lineno > max_lineno:
            max_lineno = child_end_lineno
    return max_lineno

def parse_code(x):
    x = x.lstrip('\n')
    code_lines = x.split('\n')
    module = ast.parse(x)
    code_blocks = []

    for node in module.body:
        start_lineno = node.lineno - 1  # Convert to 0-based index
        end_lineno = (getattr(node, 'end_lineno', None) or get_end_lineno(node)) - 1

        # Extract the lines corresponding to this node
        code_block_lines = code_lines[start_lineno:end_lineno+1]
        code_block = '\n'.join(code_block_lines)
        if code_block.strip():
            code_blocks.append(code_block)

    return code_blocks

# ======================================================================
# Detect if code asks for user input (don't want this during autonomous execution)
# (Implementation courtesy of ChatGPT https://chatgpt.com/share/68b07c3d-017c-8001-91cb-48f1e8edc529)
# Newer version: https://chatgpt.com/share/68e8942c-68e0-8001-98d8-70d9deff3e69
# ======================================================================

def code_asks_for_user_input(code: str) -> bool:
    try:
        tree = ast.parse(code)
        detector = InputDetector()
        detector.visit(tree)
        return detector.found
    except SyntaxError:
        return False

class InputDetector(ast.NodeVisitor):
    def __init__(self):
        self.found = False
        # Track aliases like "import sys as s" -> s
        self.sys_aliases = {"sys"}
        # Track getpass module aliases and direct getpass() imports
        self.getpass_module_aliases = {"getpass"}
        self.getpass_function_names = set()
        # Track names that hold file handles from open(...)
        self.file_handle_names = set()

    # ---- import tracking ----
    def visit_import(self, node: ast.Import):  # for Python <=3.7 compatibility
        for alias in node.names:
            if alias.name == "sys":
                self.sys_aliases.add(alias.asname or "sys")
            if alias.name == "getpass":
                self.getpass_module_aliases.add(alias.asname or "getpass")
        self.generic_visit(node)

    def visit_Import(self, node: ast.Import):  # Python 3.8+ nodes are capitalized
        self.visit_import(node)

    def visit_ImportFrom(self, node: ast.ImportFrom):
        if node.module == "getpass":
            for alias in node.names:
                # from getpass import getpass [as gpgetpass]
                if alias.name == "getpass":
                    self.getpass_function_names.add(alias.asname or "getpass")
        self.generic_visit(node)

    # ---- track file handles ----
    def _is_open_call(self, call: ast.Call) -> bool:
        f = call.func
        # open(...)
        if isinstance(f, ast.Name) and f.id == "open":
            return True
        # something.open(...)
        if isinstance(f, ast.Attribute) and f.attr == "open":
            return True
        return False

    def visit_With(self, node: ast.With):
        # with open(...) as f:
        for item in node.items:
            ctx = item.context_expr
            if isinstance(ctx, ast.Call) and self._is_open_call(ctx):
                if isinstance(item.optional_vars, ast.Name):
                    self.file_handle_names.add(item.optional_vars.id)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign):
        # f = open(...)
        if isinstance(node.value, ast.Call) and self._is_open_call(node.value):
            for tgt in node.targets:
                if isinstance(tgt, ast.Name):
                    self.file_handle_names.add(tgt.id)
        self.generic_visit(node)

    # ---- helpers ----
    def _is_sys_stdin(self, val: ast.AST) -> bool:
        # Matches sys.stdin (with sys aliases) or plain stdin if someone did "from sys import stdin"
        # Accept Attribute(Name(sys_alias), 'stdin') or Name('stdin')
        if isinstance(val, ast.Attribute) and val.attr == "stdin":
            base = val.value
            return isinstance(base, ast.Name) and base.id in self.sys_aliases
        if isinstance(val, ast.Name) and val.id == "stdin":
            return True
        return False

    def _is_file_handle_name(self, val: ast.AST) -> bool:
        return isinstance(val, ast.Name) and val.id in self.file_handle_names

    def _is_open_chain(self, val: ast.AST) -> bool:
        # open(...).read(...)
        return isinstance(val, ast.Call) and self._is_open_call(val)

    def _is_getpass_call(self, node: ast.Call) -> bool:
        f = node.func
        # direct getpass(...) if imported from getpass
        if isinstance(f, ast.Name) and f.id in self.getpass_function_names:
            return True
        # getpass.getpass(...) with module alias
        if isinstance(f, ast.Attribute) and f.attr == "getpass":
            base = f.value
            if isinstance(base, ast.Name) and base.id in self.getpass_module_aliases:
                return True
        return False

    # ---- main detection ----
    def visit_Call(self, node: ast.Call):
        # input() / raw_input()
        if isinstance(node.func, ast.Name) and node.func.id in {"input", "raw_input"}:
            self.found = True

        # getpass()
        if self._is_getpass_call(node):
            self.found = True

        # sys.stdin.read(), sys.stdin.readline()
        if isinstance(node.func, ast.Attribute) and node.func.attr in {"read", "readline"}:
            base = node.func.value
            # Only count if it's sys.stdin.* (or "stdin" imported) AND not obviously a file handle
            if self._is_sys_stdin(base):
                self.found = True
            # Exclusions: file handles and open(...).read()
            elif self._is_file_handle_name(base) or self._is_open_chain(base):
                pass
            # Otherwise: unknown object `.read()` ¡V don¡¦t assume it's user input
            else:
                pass

        self.generic_visit(node)

