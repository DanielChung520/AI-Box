import os
import re

def fix_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    changed = False
    
    # Rule 1: Remove trailing commas in class/dataclass fields and docstrings
    # This pattern matches identifier: type [= field(...)] , followed by newline or comment
    # Also matches docstrings followed by comma and newline
    
    # 1.1 Dataclass fields like: field: type = value,
    new_content = re.sub(r'(^\s+[a-zA-Z_][a-zA-Z0-9_]*\s*:\s*[^=\n#]+(?:=\s*[^#\n]+)?),\s*(#.*)?$', r'\1 \2', content, flags=re.MULTILINE)
    if new_content != content:
        content = new_content
        changed = True
        
    # 1.2 Docstrings like: """docstring""",
    new_content = re.sub(r'(""")\s*,\s*$', r'\1', content, flags=re.MULTILINE)
    if new_content != content:
        content = new_content
        changed = True

    # 1.3 Docstrings like: ''',
    new_content = re.sub(r"(''')\s*,\s*$", r"\1", content, flags=re.MULTILINE)
    if new_content != content:
        content = new_content
        changed = True

    # 1.4 Assignments like: self.x = func(),
    new_content = re.sub(r'(^\s+self\.[a-zA-Z0-9_]+\s*=\s*[^,\n#]+),\s*(#.*)?$', r'\1 \2', content, flags=re.MULTILINE)
    if new_content != content:
        content = new_content
        changed = True
        
    # 1.5 Global assignments like: _execution_engine = TaskExecutionEngine(),
    new_content = re.sub(r'(^[a-zA-Z_][a-zA-Z0-9_]*\s*=\s*[^,\n#]+),\s*(#.*)?$', r'\1 \2', content, flags=re.MULTILINE)
    if new_content != content:
        content = new_content
        changed = True

    # Rule 2: Fix unclosed/extra parentheses
    # 2.1 e.g. logger.info(f"..."")) -> logger.info(f"...")
    new_content = re.sub(r'(\)\s*)"+\s*$', r'\1', content, flags=re.MULTILINE)
    if new_content != content:
        content = new_content
        changed = True
        
    # 2.2 e.g. return CleanupResponse(..., message=f"..."")
    # This matches message=f"..." followed by one or more extra quotes and newline
    new_content = re.sub(r'(\bf?"[^"]*")"+\s*$', r'\1', content, flags=re.MULTILINE)
    if new_content != content:
        content = new_content
        changed = True

    # 2.3 Specific fix for agents/builtin/task_cleanup_agent/agent.py:78
    # return CleanupResponse(success=False, message=f"執行過程中出錯: {str(e)}""
    if 'return CleanupResponse(success=False, message=f"執行過程中出錯: {str(e)}""' in content:
        content = content.replace('return CleanupResponse(success=False, message=f"執行過程中出錯: {str(e)}""', 
                                  'return CleanupResponse(success=False, message=f"執行過程中出錯: {str(e)}")')
        changed = True

    # 2.4 Extra closing parenthesis
    # e.g. timed out (attempt {attempt + 1}"))
    new_content = re.sub(r'(\(attempt \{attempt \+ 1\}\)")\)\)', r'\1)', content)
    if new_content != content:
        content = new_content
        changed = True

    # 2.5 Missing closing bracket in cloned.add_audit_entry
    if 'cloned.add_audit_entry("state_cloned", {"from_state": state.session_id}' in content:
        content = content.replace('cloned.add_audit_entry("state_cloned", {"from_state": state.session_id}',
                                  'cloned.add_audit_entry("state_cloned", {"from_state": state.session_id})')
        changed = True

    # Rule 3: Trailing commas in function calls that shouldn't be there (e.g. self.logger.info(...),)
    new_content = re.sub(r'(\.info\([^)]+\)),\s*$', r'\1', content, flags=re.MULTILINE)
    if new_content != content:
        content = new_content
        changed = True

    if changed:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

# Target directories
dirs = [
    'agents/builtin/task_cleanup_agent',
    'api/routers',
    'genai/workflows/langgraph'
]

for d in dirs:
    full_path = os.path.join('/Users/daniel/GitHub/AI-Box', d)
    if not os.path.exists(full_path):
        continue
    for root, _, files in os.walk(full_path):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if fix_file(file_path):
                    print(f"Fixed {file_path}")

# Also fix the specific files we identified earlier
fix_file('/Users/daniel/GitHub/AI-Box/genai/workflows/langgraph/engine.py')
fix_file('/Users/daniel/GitHub/AI-Box/genai/workflows/langgraph/state.py')
fix_file('/Users/daniel/GitHub/AI-Box/genai/workflows/langgraph/nodes.py')
