import os
import re

def fix_line(line):
    # 1. Fix malformed .get() calls: .get(arg1, arg2)) -> .get(arg1, arg2)
    # This also handles cases where there's no closing parenthesis yet.
    line = re.sub(r'\.get\(([^,)]+)\),\s*([^,)]+)', r'.get(\1, \2)', line)
    
    # 2. Fix truncated str(e, at end of line)
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
    
    # 6. Fix unmatched parentheses and misplaced colons
    # Example: isinstance(..., get(...):) -> isinstance(..., get(...)):
    if line.endswith(':)'):
        line = line[:-2] + '):'
    elif line.endswith(':))'):
        line = line[:-3] + ')): ' # wait, maybe just :
        line = line.replace(':))', ')):')

    # General count-based fix for missing parentheses at end of line (but before colon)
    if line.strip().endswith(':'):
        # Count parens in the part before the colon
        prefix = line.rstrip().rstrip(':')
        diff = prefix.count('(') - prefix.count(')')
        if diff > 0:
            line = prefix + (')' * diff) + ':'
    else:
        diff = line.count('(') - line.count(')')
        if diff > 0 and not line.strip().endswith(')'):
             # Only add if it looks like a function call or expression
             if re.search(r'\(', line)):
                 line = line.rstrip() + (')' * diff)

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
    # List of directories to check
    dirs = ['.', 'api', 'agents', 'services', 'llm', 'mcp', 'database', 'storage', 'system', 'workers', 'tools', 'genai', 'kag', 'monitoring']
    for d in dirs:
        if not os.path.exists(d): continue
        if os.path.isfile(d) and d.endswith('.py'):
            if fix_file(d): fixed_count += 1
            continue
        for root, _, files in os.walk(d):
            if any(x in root for x in ['venv', '.git', '__pycache__']): continue
            for file in files:
                if file.endswith('.py'):
                    if fix_file(os.path.join(root, file)):
                        fixed_count += 1
    print(f"Total files fixed: {fixed_count}")

if __name__ == "__main__":
    fix_all_files()
