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
    
    # Common broken patterns where ( was replaced by () at end of line
    broken_calls = [
        'AgentServiceResponse()',
        'AgentServiceRequest()',
        'AgentServiceStatus()',
        'ConversionResponse()',
        'ConversionConfig()',
        'LLMNodeConfig()',
        'LLMNodeRouter()',
        'CostEstimate()',
        'self.logger.warning()',
        'self.logger.error()',
        'logger.info()',
        'logger.warning()',
        'logger.error()',
        'self.logger.info()',
        'logging.info()',
        'logging.warning()',
        'logging.error()',
    ]

    for i in range(len(lines)):
        line = lines[i]
        stripped = line.strip()
        
        # 1. Fix broken imports
        if 'import (' in line:
            line = line.replace('import (', 'import (')
            modified = True
            
        # 2. Fix broken multi-line calls
        for call in broken_calls:
            if stripped.endswith(call):
                # Check if next line is more indented, which suggests this should be a ()
                if i + 1 < len(lines):
                    next_line = lines[i+1]
                    if next_line.startswith(line[:line.find(stripped)] + '    '):
                        line = line.replace(call, call[:-1]) # Remove the last )
                        modified = True
                        break
        
        # 3. Fix missing comma in multi-line constructor
        # If line ends with ) but next line is a keyword argument (e.g., key=value)
        if stripped.endswith(')') and not stripped.endswith('):') and not stripped.endswith('),'):
             if i + 1 < len(lines):
                next_line = lines[i+1].strip()
                if '=' in next_line and not next_line.startswith('if ') and not next_line.startswith('elif '):
                     # Likely missing a comma
                     # But only if it's like error=str(e)
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
