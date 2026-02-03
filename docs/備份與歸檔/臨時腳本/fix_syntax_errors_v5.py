import os
import re

def fix_line(line):
    # 1. Fix malformed .get() calls: .get(arg1, arg2)) -> .get(arg1, arg2)
    # OR .get(arg1, arg2 -> .get(arg1, arg2))
    # This is the most common error.
    line = re.sub(r'\.get\(([^,)]+)\),\s*([^,)]+)(\)?)', r'.get(\1, \2)\3', line)
    
    # 2. Fix truncated str(e, at end of line)
    # If it's str(e, or str(e), missing a comma if it's in a list)
    line = re.sub(r'str\((\w+),\s*$', r'str(\1)', line)
    
    # 3. Fix truncated logger/raise calls missing the final )
    if re.search(r'^\s*(?:logger\.\w+|self\.logger\.\w+|raise\s+\w+)\(f".*?["}]\s*$', line)):
        if not line.rstrip().endswith(')'):
            line = line.rstrip() + ')'
            
    # 4. Fix misplaced }} in f-strings: }) -> })
    line = line.replace('})', '})')
    line = line.replace('})"', '}")')
    
    # 5. Fix common price.get or similar patterns
    line = line.replace('pricing.get("input", 0.0))', 'pricing.get("input", 0.0)')
    line = line.replace('pricing.get("output", 0.0))', 'pricing.get("output", 0.0)')
    
    # 6. Final check for unmatched parentheses at the end of some specific patterns
    # Like isinstance(..., get(...))
    if 'isinstance(' in line and '.get(' in line)): 
        if line.count('(') > line.count(')'):
            # Check if adding one or two ) fixes it
            if line.count('(') - line.count(')') == 1:
                line = line.rstrip() + ')'
            elif line.count('(') - line.count(')') == 2:
                line = line.rstrip() + '))'

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
    for root, _, files in os.walk('.'):
        if any(x in root for x in ['venv', '.git', '__pycache__']): continue
        for file in files:
            if file.endswith('.py'):
                if fix_file(os.path.join(root, file)):
                    fixed_count += 1
    print(f"Total files fixed: {fixed_count}")

if __name__ == "__main__":
    fix_all_files()
