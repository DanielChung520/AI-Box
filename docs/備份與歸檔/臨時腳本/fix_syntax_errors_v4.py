import os
import re

def fix_line(line):
    # 1. Fix malformed .get() calls: .get(arg1, arg2) -> .get(arg1, arg2)
    # Handles cases like: .get("key", default) or .get(var, default)
    # We match .get( followed by non-comma/non-paren, then ), then optional space, then non-paren, then )
    line = re.sub(r'\.get\(([^,)]+)\),\s*([^)]+)\)', r'.get(\1, \2)', line)
    
    # 2. Fix truncated str(e, at end of line)
    line = re.sub(r'str\(([^,)]+),\s*$', r'str(\1)', line)
    
    # 3. Fix truncated logger/raise calls missing the final )
    # Pattern: something(f"...")
    # If it ends with " or } or }", and it's a known function call that should be closed.
    if re.search(r'^\s*(?:logger\.\w+|self\.logger\.\w+|raise\s+\w+)\(f".*?["}]\s*$', line)):
        if not line.rstrip().endswith(')'):
            line = line.rstrip() + ')'
            
    # 4. Fix the specific pattern: .get("key", default), at end of line
    # (Happens in dictionaries or function arguments)
    line = re.sub(r'\.get\(([^,)]+)\),\s*([^,)]+)\),', r'.get(\1, \2),', line)

    # 5. Fix misplaced }} in f-strings: }) -> })
    # Only if it looks like a function call ending.
    line = line.replace('})', '})')
    line = line.replace('})"', '}")')
    
    # 6. Fix specific case in cost_estimator.py and others: pricing.get("input", 0.0)
    line = line.replace('pricing.get("input", 0.0)', 'pricing.get("input", 0.0)')
    line = line.replace('pricing.get("output", 0.0)', 'pricing.get("output", 0.0)')

    # 7. Fix truncated dict entry: "error": str(e)
    line = re.sub(r'(":?\s*)str\((\w+),\s*$', r'\1str(\2)', line)

    return line

def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return False

    modified = False
    new_lines = []
    for line_content in lines:
        stripped = line_content.rstrip('\n')
        fixed = fix_line(stripped)
        if fixed != stripped:
            new_lines.append(fixed + '\n')
            modified = True
        else:
            new_lines.append(line_content)

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return True
    return False

def fix_all_files():
    fixed_count = 0
    # Search for all python files in the repo
    for root, _, files in os.walk('.'):
        if any(x in root for x in ['venv', '.git', '__pycache__']): continue
        for file in files:
            if file.endswith('.py'):
                if fix_file(os.path.join(root, file)):
                    fixed_count += 1
    print(f"Total files fixed: {fixed_count}")

if __name__ == "__main__":
    fix_all_files()
