
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

