import json
import subprocess
import os

def get_ruff_errors(path):
    cmd = ['ruff', 'check', path, '--select', 'E9', '--output-format', 'json']
    result = subprocess.run(cmd, capture_output=True, text=True)
    if not result.stdout:
        return []
    try:
        return json.loads(result.stdout)
    except:
        return []

def fix_file(file_path):
    errors = get_ruff_errors(file_path)
    if not errors:
        return False
    
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    changed = False
    # Track which rows we've fixed to avoid multiple commas on same line
    fixed_rows = set()
    
    # Sort errors by row DESCENDING so we don't mess up line numbers if we were to add lines
    # (Though we are only adding characters at the end of existing lines)
    errors.sort(key=lambda x: x['location']['row'], reverse=True)
    
    for error in errors:
        row = error['location']['row'] - 1
        msg = error['message']
        if row < 0 or row >= len(lines): continue
        if row in fixed_rows: continue
        
        line = lines[row]
        
        # 1. Missing comma in list/dict/call
        # Error messages often look like: Expected ')', found newline
        if 'Expected \')\', found newline' in msg or 'Expected \']\', found newline' in msg or 'Expected \'}\', found newline' in msg:
            # Add a comma at the end of the line (before newline)
            lines[row] = line.rstrip() + ',\n'
            changed = True
            fixed_rows.add(row)
            print(f"Added comma to {file_path}:{row+1}")
            
        # 2. Docstring issues (if any left)
        elif 'missing closing quote' in msg or 'Simple statements must be separated' in msg:
            if '"""' in line and line.strip().endswith('""'):
                lines[row] = line.replace('""\n', '"""\n')
                changed = True
                fixed_rows.add(row)
                print(f"Fixed docstring in {file_path}:{row+1}")
            elif "'''" in line and line.strip().endswith("''"):
                lines[row] = line.replace("''\n", "'''\n")
                changed = True
                fixed_rows.add(row)
                print(f"Fixed docstring in {file_path}:{row+1}")

    if changed:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return True
    return False

if __name__ == "__main__":
    # Target files we know have many errors
    files_to_check = []
    target_dirs = [
        'genai/workflows/langgraph',
        'agents/builtin/task_cleanup_agent',
        'database/qdrant',
        'api/routers'
    ]
    for d in target_dirs:
        full_path = os.path.join('/Users/daniel/GitHub/AI-Box', d)
        if not os.path.exists(full_path): continue
        for root, _, files in os.walk(full_path):
            for file in files:
                if file.endswith('.py'):
                    files_to_check.append(os.path.join(root, file))
    
    for p in files_to_check:
        # Run multiple times to catch cascading errors
        for _ in range(5):
            if not fix_file(p):
                break
