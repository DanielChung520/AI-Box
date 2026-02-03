import os

def fix_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {filepath}: {e}")
        return False

    modified = False
    new_lines = []
    
    for i in range(len(lines)):
        line = lines[i]
        stripped = line.strip()
        
        # 1. Fix broken imports
        if 'import (' in line:
            line = line.replace('import (', 'import (')
            modified = True
            
        # 2. Fix broken multi-line calls
        if stripped.endswith('()'):
             # Exclude control flow and definitions
             if not any(stripped.startswith(x) for x in ['if ', 'elif ', 'while ', 'def ', 'except ']):
                # Check if next line is more indented
                if i + 1 < len(lines):
                    next_line = lines[i+1]
                    # Current indentation
                    indent = line[:line.find(stripped)]
                    if next_line.startswith(indent + '    '):
                        line = line.replace('()', '(')
                        modified = True
        
        # 3. Fix missing comma in multi-line constructor/call
        if stripped.endswith(')') and not any(stripped.endswith(x) for x in ['):', '),', '): ', '), ']):
             if i + 1 < len(lines):
                next_line = lines[i+1].strip()
                if '=' in next_line and not any(next_line.startswith(x) for x in ['if ', 'elif ', 'while ', 'for ']):
                     # If it's a known pattern like error=str(e), add a comma
                     if 'error=str(e)' in line:
                         line = line.replace('str(e)', 'str(e),')
                         modified = True

        new_lines.append(line)

    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        return True
    return False

def fix_all_files():
    fixed_count = 0
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
