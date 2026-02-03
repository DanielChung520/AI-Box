import os
import re

def fix_docstrings_only(content):
    # Fix docstrings/f-strings ending with the wrong number of quotes
    # Only target ending in exactly "" or """" etc, not touching commas.
    content = re.sub(r'(""".*?)""(\s*)$', r'\1"""\2', content, flags=re.MULTILINE)
    content = re.sub(r'(""".*?)""""+(\s*)$', r'\1"""\2', content, flags=re.MULTILINE)
    content = re.sub(r'(f""".*?)"(\s*)$', r'\1"""\2', content, flags=re.MULTILINE)
    return content

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
                    # Check if file is untracked or if it's one of the ones we know had issues
                    # Actually, we can just check all .py files in these dirs
                    with open(p, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = fix_docstrings_only(content)
                    
                    if new_content != content:
                        with open(p, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"Fixed quotes in {p}")
