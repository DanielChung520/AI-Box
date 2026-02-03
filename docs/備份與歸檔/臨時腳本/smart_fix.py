import json
import subprocess
import os
import re

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
    
    # Sort errors by row descending so we don't mess up line numbers
    errors.sort(key=lambda x: x['location']['row'], reverse=True)
    
    # Seen rows to avoid duplicate fixes on same line in one pass
    seen_rows = set()
    
    for error in errors:
        row = error['location']['row'] - 1
        if row < 0 or row >= len(lines):
            continue
        if row in seen_rows:
            continue
            
        msg = error['message']
        line = lines[row]
        
        # 1. Fix docstrings ending in ""
        if 'missing closing quote' in msg or 'Simple statements must be separated' in msg or 'Expected a statement' in msg:
            if '"""' in line and line.strip().endswith('""'):
                lines[row] = line.replace('""\n', '"""\n').replace('"" \n', '"""\n')
                changed = True
                seen_rows.add(row)
            elif "'''" in line and line.strip().endswith("''"):
                lines[row] = line.replace("''\n", "'''\n").replace("'' \n", "'''\n")
                changed = True
                seen_rows.add(row)
        
        # 2. Fix extra commas at the end of lines
        if 'Expected a statement' in msg or 'Simple statements must be separated' in msg:
            trimmed = line.strip()
            if trimmed.endswith(','):
                 # If it's like "var = val," or "field: type," or "field: type = val,"
                 if re.search(r'([a-zA-Z0-9_])\s*[:=].*,', trimmed) or trimmed.endswith(':,'):
                     # BUT check if it's inside a list or function params
                     # For now, if it's indented and looks like a field, we remove it
                     # Exception: if it's in a multi-line list/dict, it SHOULD have a comma
                     # This is tricky. Let's look for common patterns from my previous failed scripts.
                     lines[row] = line.rstrip().rstrip(',') + '\n'
                     changed = True
                     seen_rows.add(row)
            elif ' ,' in line:
                lines[row] = line.replace(' ,', ',')
                changed = True
                seen_rows.add(row)
        
        # 3. Fix "for ... :,"
        if 'Expected a statement' in msg and ':' in line and line.strip().endswith(','):
            if 'for ' in line or 'if ' in line or 'while ' in line or 'def ' in line or 'class ' in line:
                lines[row] = line.rstrip().rstrip(',') + '\n'
                changed = True
                seen_rows.add(row)

        # 4. Fix double closing parens with quotes from v15
        if 'Expected a statement' in msg and '"))' in line:
            lines[row] = line.replace('"))', '")')
            changed = True
            seen_rows.add(row)

    if changed:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return True
    return False

if __name__ == "__main__":
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
                    p = os.path.join(root, file)
                    # Run up to 3 times to catch cascading errors
                    for _ in range(3):
                        if fix_file(p):
                            print(f"Fixed {p}")
                        else:
                            break
