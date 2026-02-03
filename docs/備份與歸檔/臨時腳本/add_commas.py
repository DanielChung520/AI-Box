import os
import re

def add_commas(content):
    lines = content.splitlines()
    new_lines = []
    paren_balance = 0
    
    for i, line in enumerate(lines):
        # Update paren balance
        paren_balance += line.count('(') - line.count(')')
        
        # If we are inside parens and this line doesn't end with a comma, paren, or comment
        stripped = line.strip()
        if paren_balance > 0 and stripped and not stripped.endswith(',') and not stripped.endswith('(') and not stripped.endswith(')') and not stripped.startswith('#'):
            # Check if next line starts with an identifier or a closing paren
            # This is a bit risky but let's try
            if i + 1 < len(lines):
                next_stripped = lines[i+1].strip()
                if next_stripped and (re.match(r'[a-zA-Z_]', next_stripped) or next_stripped.startswith(')')):
                    # Check if current line looks like it needs a comma (e.g. key=value or just value)
                    if re.search(r'[a-zA-Z0-9_"\']\s*$', stripped):
                        line = line + ','
        
        new_lines.append(line)
        
    return '\n'.join(new_lines)

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
                    
                    new_content = add_commas(content)
                    
                    if new_content != content:
                        with open(p, 'w', encoding='utf-8') as f:
                            f.write(new_content)
                        print(f"Added commas in {p}")
