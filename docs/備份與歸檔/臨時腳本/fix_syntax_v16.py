import re
import sys

def fix_docstrings(content):
    # Fix docstrings ending in "" instead of """
    # This specifically looks for lines that start with optional indentation, then """ and some text, ending in exactly ""
    pattern = r'(\s*"""[^"]*?)""(\s*$)'
    return re.sub(pattern, r'\1"""\2', content, flags=re.MULTILINE)

def add_missing_commas_in_init(content):
    # Specifically for the RouteDecision.__init__ pattern seen in routing.py
    # target_node: str 
    # confidence: float = 1.0 
    # ...
    # We look for lines in an __init__ or similar that look like parameter definitions missing a comma
    pattern = r'(^\s+[a-zA-Z_][a-zA-Z0-9_]*\s*:\s*[^,\n#]+)(\s*#.*)?$'
    
    lines = content.splitlines()
    new_lines = []
    in_function_params = False
    
    for line in lines:
        if 'def ' in line and '(' in line:
            in_function_params = True
        
        if in_function_params:
            # If line has ) and maybe : it's the end of params
            if ')' in line:
                in_function_params = False
            
            # If it's a param line and doesn't end in comma and isn't the last line of params
            # This is hard to get 100% right with regex, so let's be conservative
            if re.match(r'^\s+[a-zA-Z_][a-zA-Z0-9_]*\s*:\s*[^,\n#]+$', line):
                 # Don't add if it's the line with ')'
                 if ')' not in line:
                     line = line + ','
        
        new_lines.append(line)
    
    return '\n'.join(new_lines)

def fix_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Fix docstrings
    content = fix_docstrings(content)
    
    # 2. Add missing commas in parameter lists (conservative approach)
    # Actually, let's just use a simpler regex for the commas that targets the specific observed issue
    # Identifier: Type [= Default] followed by newline
    content = re.sub(r'(^\s+[a-zA-Z_][a-zA-Z0-9_]*\s*:\s*[^,\n#\)]+)\s*$', r'\1,', content, flags=re.MULTILINE)
    
    # 3. Fix the extra quote issue from v15
    # e.g. message=f"..."") -> message=f"...")
    content = re.sub(r'(\bf?"[^"]*")"+\s*(\))', r'\1\2', content)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)

if __name__ == "__main__":
    fix_file(sys.argv[1])
