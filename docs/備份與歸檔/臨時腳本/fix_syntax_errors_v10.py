# 代碼功能說明: 批量修復語法錯誤 (v10)
# 創建日期: 2026-01-24
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-24

import os
import re
from pathlib import Path

def fix_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Error reading {path}: {e}")
        return False

    lines = content.splitlines()
    new_lines = []
    changed = False

    for i, line in enumerate(lines):
        new_line = line
        stripped = line.strip()

        # 1. 修復錯誤的 super().__init__()
        if 'super().__init__(' in line:
            new_line = line.replace('super().__init__(', 'super().__init__(')
            changed = True

        # 2. 修復行尾多餘的引號 (Fix extra quotes at end of line)
        if line.count('f"') >= 1:
            if stripped.endswith('")"'):
                new_line = line.rstrip()[:-2] + '"'
                changed = True
            elif stripped.endswith('")'):
                if line.count('")') == 2 and line.count('f"') == 1:
                    new_line = line.rstrip()[:-2]
                    changed = True

        # 3. 修復 f-string 中的 {var} (Fix {var} in f-strings)
        if '{' in new_line and ')}' in new_line:
            # 廣泛匹配 {var} 或 {var.attr} 或 {func()}
            new_line = re.sub(r'\{([a-zA-Z_][a-zA-Z0-9_.]*(?:\(\))?)\)\}', r'{\1}', new_line)
            if new_line != line:
                changed = True
        
        # 4. 修復字典中的 key: val}
        if ')}' in new_line and ':' in new_line and not new_line.strip().startswith('f"'):
             new_line = re.sub(r':\s*([a-zA-Z_][a-zA-Z0-9_.]*)\)\}', r': \1}', new_line)
             if new_line != line:
                 changed = True

        # 5. 修復單獨一行的逗號應該是 ), 的情況
        if stripped == ',':
            if i > 0:
                prev_line = lines[i-1].strip()
                # 如果前一行以引號、右括號、右中括號或右大括號結尾
                if any(prev_line.endswith(c) for c in ['"', "'", ']', '}', ')']):
                    if i + 1 < len(lines):
                        next_line = lines[i+1].strip()
                        if '=' in next_line or next_line.startswith(')') or next_line.startswith(']') or next_line.startswith('}'):
                            new_line = line.replace(',', '),')
                            changed = True

        # 6. 修復函數定義或調用被截斷的情況 (僅替換行尾的 ())
        if stripped.endswith('()'):
            if i + 1 < len(lines):
                next_line = lines[i+1].expandtabs()
                line_expanded = line.expandtabs()
                current_indent = len(line_expanded) - len(line_expanded.lstrip())
                next_indent = len(next_line) - len(next_line.lstrip())
                
                if next_indent > current_indent:
                    if any(stripped.startswith(p) for p in ['def ', 'class ', 'if ', 'elif ', 'while ', 'for ']) or \
                       'any()' in stripped or 'all()' in stripped or 'AgentServiceResponse()' in stripped or \
                       'NodeResult.success()' in stripped or 'NodeResult.failure()' in stripped:
                        # 僅替換最後一個 ()
                        if line.rstrip().endswith('()'):
                            new_line = line.rstrip()[:-2] + '('
                            changed = True

        # 7. 修復 logger.info(...) 結尾的 ",
        if 'logger.' in stripped and (stripped.endswith('",))') or stripped.endswith('", )')):
             new_line = line.replace('",))', '",').replace('", )', '",')
             changed = True

        # 8. 修復 f-string 中遺漏的 }
        if 'f"' in line and '{' in line:
            # 簡單檢查：如果 line 中有 { 且之後沒有 }
            braces = 0
            for char in line:
                if char == '{': braces += 1
                if char == '}': braces -= 1
            if braces > 0:
                if line.rstrip().endswith('")'):
                     new_line = line.rstrip()[:-2] + '}")'
                     changed = True
                elif line.rstrip().endswith('",'):
                     new_line = line.rstrip()[:-2] + '}",'
                     changed = True

        new_lines.append(new_line)

    if changed:
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(new_lines) + '\n')
            return True
        except Exception as e:
            print(f"Error writing {path}: {e}")
            return False
    return False

def main():
    target_dirs = [
        'agents', 'api', 'services', 'genai', 'llm', 'database', 'docs', 'storage', 'system', 'workers'
    ]
    
    total_fixed = 0
    for d in target_dirs:
        if not os.path.exists(d): continue
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith('.py'):
                    path = os.path.join(root, file)
                    if fix_file(path):
                        print(f"Fixed: {path}")
                        total_fixed += 1
    
    for file in os.listdir('.'):
        if file.endswith('.py') and os.path.isfile(file):
            if fix_file(file):
                print(f"Fixed: {file}")
                total_fixed += 1
                
    print(f"Total files fixed: {total_fixed}")

if __name__ == "__main__":
    main()
