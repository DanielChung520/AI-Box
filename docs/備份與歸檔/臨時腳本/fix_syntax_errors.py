import os
import re

def fix_line(line):
    # 1. Fix the double-brace-closing-parenthesis error: }") -> }")
    line = line.replace('}")', '}")')
    line = line.replace('}")"', '}")')
    
    # 2. Fix misplaced braces in content: content}) -> content})
    line = line.replace('content})', 'content})')
    
    # 3. Fix missing/extra parenthesis in get() or other calls
    # Pattern: .get(arg1, arg2) -> .get(arg1, arg2)
    # This matches .get("something", default) or .get("something", default),
    line = re.sub(r'\.get\(([^)]+)\),\s*([^)]+)\)', r'.get(\1, \2)', line)
    
    # 4. Fix missing parenthesis in .get("something" followed by } or ,)
    line = re.sub(r'(\.get\("[^"]+")(\s*[},])', r'\1)\2', line)
    
    # 5. Fix truncated function calls with f-strings
    if re.search(r'^\s*(?:\w+(?:\.\w+)*)\(f".*?"\s*$', line)):
        if not line.rstrip().endswith(')'):
            line = line.rstrip() + ')'
    if re.search(r'^\s*(?:\w+(?:\.\w+)*)\(f".*?\{.*?\}\s*$', line)):
         if not line.rstrip().endswith(')'):
            line = line.rstrip() + ')'

    # 6. Specific fix for raise ... )" from e -> ") from e
    line = line.replace('}") from e', '}") from e')
    line = line.replace('}")" from e', '}") from e')
    line = line.replace('{exc}")" from exc', '{exc}") from exc')
    
    # 7. Fix the pricing.get(...) pattern in cost_estimator.py specifically if needed
    # (pricing.get("input", 0.0) -> pricing.get("input", 0.0)
    line = line.replace('pricing.get("input", 0.0)', 'pricing.get("input", 0.0)')
    line = line.replace('pricing.get("output", 0.0)', 'pricing.get("output", 0.0)')

    # 8. Fix the extra ), at the end of lines in cost_estimator.py
    # Example: self.model_pricing.get("gpt-oss:20b", {"input": 0.0, "output": 0.0}),
    if 'model_pricing.get' in line and line.strip().endswith('),'):
        line = line.replace('),', '),') # no change, but wait
        # Let's try to fix the specific line 105 pattern
        line = re.sub(r'(model_pricing\.get\(.*?\)),\s*(\{.*?\})\),', r'\1, \2),', line)

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
        # print(f"Fixed: {filepath}")
        return True
    return False

def fix_all_files():
    fixed_count = 0
    dirs_to_fix = ['.', 'api', 'agents', 'services', 'llm', 'mcp', 'database', 'storage', 'system', 'workers', 'tools', 'genai', 'kag', 'monitoring']
    for d in dirs_to_fix:
        if not os.path.exists(d): continue
        if os.path.isfile(d):
            if d.endswith('.py'):
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
