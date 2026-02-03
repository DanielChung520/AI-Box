import json
import subprocess
import os
import re
from datetime import datetime

# Debug Mode Configuration
LOG_PATH = "/Users/daniel/GitHub/AI-Box/.cursor/debug.log"
SESSION_ID = "debug-session-master-fixer-v5"

def log_debug(message, data=None, hypothesis_id=None):
    log_entry = {
        "id": f"log_{int(datetime.now().timestamp())}_{os.urandom(4).hex()}",
        "timestamp": int(datetime.now().timestamp() * 1000),
        "location": "master_fixer.py",
        "message": message,
        "data": data or {},
        "sessionId": SESSION_ID,
        "hypothesisId": hypothesis_id
    }
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_entry) + "\n")

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
    fixed_rows = set()
    
    # Sort errors by row DESCENDING
    errors.sort(key=lambda x: x['location']['row'], reverse=True)
    
    for error in errors:
        row = error['location']['row'] - 1
        msg = error['message']
        if row < 0 or row >= len(lines): continue
        if row in fixed_rows: continue
        
        line = lines[row]
        stripped = line.strip()
        
        # 1. Hypothesis H: Malformed characters (full-width comma or colon)
        if '，' in line or '：' in line:
            lines[row] = line.replace('，', ',').replace('：', ':')
            changed = True
            fixed_rows.add(row)
            log_debug(f"Replaced full-width char", {"file": file_path, "line": row+1}, "H")
            continue

        # 2. Hypothesis E: Trailing comma in control statements or global
        if any(stripped.startswith(kw) for kw in ['if ', 'elif ', 'for ', 'global ', 'return ']):
            if stripped.endswith(','):
                lines[row] = line.rstrip().rstrip(',') + '\n'
                changed = True
                fixed_rows.add(row)
                log_debug(f"Removed trailing comma from keyword line", {"file": file_path, "line": row+1}, "E")
                continue

        # 3. Hypothesis G: Missing colons
        if any(stripped.startswith(kw) for kw in ['if ', 'elif ', 'for ', 'def ', 'with ', 'while ']):
            if not stripped.endswith(':') and not stripped.endswith('\\'):
                # Check if it's a multi-line header (ends with '(' or '[')
                if not any(c in stripped for c in '([{'):
                    lines[row] = line.rstrip() + ':\n'
                    changed = True
                    fixed_rows.add(row)
                    log_debug(f"Added missing colon", {"file": file_path, "line": row+1}, "G")
                    continue

        # 4. Hypothesis F: Truncated strings
        if "unterminated string literal" in msg or "missing closing quote" in msg:
            if stripped.endswith('"') and not stripped.endswith('"""'):
                # Heuristic: if it's 'return "' or 'reasoning: str = "'
                if stripped.endswith(' "'):
                    lines[row] = line.rstrip() + '""\n'
                    changed = True
                    fixed_rows.add(row)
                    log_debug(f"Fixed truncated string", {"file": file_path, "line": row+1}, "F")
                    continue
                elif stripped == '"':
                    lines[row] = line.replace('"', '"""\n')
                    changed = True
                    fixed_rows.add(row)
                    log_debug(f"Fixed single quote docstring", {"file": file_path, "line": row+1}, "F")
                    continue

        # 5. Hypothesis F: Truncated function calls (missing closing parenthesis)
        if "(" in stripped and not ")" in stripped and (stripped.endswith(",") or stripped.endswith(")") == False):
            if "Expected `)`, found" in msg or "'(' was never closed" in msg:
                lines[row] = line.rstrip().rstrip(",") + ")\n"
                changed = True
                fixed_rows.add(row)
                log_debug(f"Added missing closing parenthesis", {"file": file_path, "line": row+1}, "F")
                continue

        # 6. Hypothesis E: Comma before keyword on next line
        if row + 1 < len(lines):
            next_stripped = lines[row+1].strip()
            if next_stripped.startswith('for ') or next_stripped.startswith('if '):
                if stripped.endswith(','):
                    lines[row] = line.rstrip().rstrip(',') + '\n'
                    changed = True
                    fixed_rows.add(row)
                    log_debug(f"Removed comma before next-line keyword", {"file": file_path, "line": row+1}, "E")
                    continue

        # 7. Unmatched parenthesis
        if "unmatched ')'" in msg and stripped.endswith('))'):
            lines[row] = line.rstrip()[:-1] + '\n'
            changed = True
            fixed_rows.add(row)
            log_debug(f"Removed unmatched parenthesis", {"file": file_path, "line": row+1}, "A")
            continue

        # 8. Non-ASCII bytes
        if "bytes can only contain ASCII" in msg:
            match = re.search(r'b"([^"]*)"', line)
            if match:
                content = match.group(1)
                lines[row] = line.replace(f'b"{content}"', f'"{content}".encode("utf-8")')
                changed = True
                fixed_rows.add(row)
                log_debug(f"Fixed non-ASCII bytes literal", {"file": file_path, "line": row+1}, "A")
                continue

    if changed:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        return True
    return False

if __name__ == "__main__":
    log_debug("Starting Master Fixer run v5")
    
    result = subprocess.run(['git', 'ls-files'], capture_output=True, text=True)
    files_to_check = [f for f in result.stdout.splitlines() if f.endswith('.py')]
    
    total_files_affected = 0
    for p in files_to_check:
        full_path = os.path.join('/Users/daniel/GitHub/AI-Box', p)
        if not os.path.exists(full_path): continue
        
        file_changed = False
        for _ in range(10):
            if fix_file(full_path):
                file_changed = True
            else:
                break
        if file_changed:
            total_files_affected += 1
    
    log_debug("Master Fixer run completed v5", {"total_files_affected": total_files_affected})
