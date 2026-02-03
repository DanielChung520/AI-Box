import os
import re

def fix_quotes(content):
    # Fix docstrings/f-strings ending with the wrong number of quotes
    # 1. Ending with 2, 4, 5, 6, 7 quotes -> replace with 3
    # Use a positive lookbehind to ensure we are at the end of a line or followed by spaces
    content = re.sub(r'("""){1,2}("+)(\s*)$', r'"""\3', content, flags=re.MULTILINE)
    # Wait, the above might be too complex. Let's simplify.
    
    # 2. Specifically fix the cases we saw:
    # """ ... ""
    content = re.sub(r'(""".*?)""(\s*)$', r'\1"""\2', content, flags=re.MULTILINE)
    # """ ... """" or """ ... """"" etc
    content = re.sub(r'(""".*?)""""+(\s*)$', r'\1"""\2', content, flags=re.MULTILINE)
    # f""" ... "
    content = re.sub(r'(f""".*?)"(\s*)$', r'\1"""\2', content, flags=re.MULTILINE)
    
    # 3. Fix missing commas in RouteDecision pattern (space then comma)
    content = content.replace(' ,', ',')
    
    # 4. Remove comma at the end of certain lines (for, if, while, assignments)
    # This was a major source of errors in v15
    content = re.sub(r'(^\s*for\s+.*?:),(\s*)$', r'\1\2', content, flags=re.MULTILINE)
    content = re.sub(r'(^\s*if\s+.*?:),(\s*)$', r'\1\2', content, flags=re.MULTILINE)
    content = re.sub(r'(^\s*def\s+.*?:),(\s*)$', r'\1\2', content, flags=re.MULTILINE)
    content = re.sub(r'(^\s*[a-zA-Z_][a-zA-Z0-9_]*\s*[:=]\s*[^,\n#]+),(\s*)$', r'\1\2', content, flags=re.MULTILINE)

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
                    with open(p, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    new_content = fix_quotes(content)
                    
                    if new_content != content:
                        with open(p, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"Fixed {p}")
