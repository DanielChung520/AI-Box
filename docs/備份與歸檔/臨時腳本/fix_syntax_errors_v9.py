# 代碼功能說明: 批量修復語法錯誤 (v9)
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

        # 1. 修復行尾多餘的引號 (Fix extra quotes at end of line)
        # Example: f"..."")" or f"..."")
        if line.count('f"') >= 1:
            if stripped.endswith('")"'):
                new_line = line.rstrip()[:-2] + '"'
                changed = True
            elif stripped.endswith('")'):
                # 只有在 f" 之後有兩個 ") 且只有一個 f" 時才修復
                if line.count('")') == 2 and line.count('f"') == 1:
                    new_line = line.rstrip()[:-2]
                    changed = True

        # 2. 修復 f-string 中的 {var} (Fix {var} in f-strings)
        if '{' in new_line and ')}' in new_line:
            # message=f"拒絕執行 ({analysis.risk_level}，...
            # 我們要將 {var} 替換為 {var}
            # 這裡使用正則表達式，確保只匹配變數名後接 )}
            new_line = re.sub(r'\{([a-zA-Z_][a-zA-Z0-9_.]*)\)\}', r'{\1}', new_line)
            # 也要處理 ( {var} ) 變成 ({var}) 的情況，但這裡先處理錯誤的 {var}
            if new_line != line:
                changed = True

        # 3. 修復單獨一行的逗號應該是 ), 的情況 (Fix stray comma that should be ),)
        if stripped == ',':
            if i > 0:
                prev_line = lines[i-1].strip()
                # 如果前一行以逗號、左中括號或左大括號結尾，且下一行是關鍵字參數或右括號
                if prev_line.endswith(',') or prev_line.endswith('[') or prev_line.endswith('{') or prev_line.endswith('('):
                    if i + 1 < len(lines):
                        next_line = lines[i+1].strip()
                        if '=' in next_line or next_line.startswith(')') or next_line.startswith(']') or next_line.startswith('}'):
                            new_line = line.replace(',', '),')
                            changed = True

        # 4. 修復函數定義或調用被截斷的情況 (Fix truncated function defs or calls)
        # Example: def func() -> def func()
        if stripped.endswith('()'):
            if i + 1 < len(lines):
                next_line = lines[i+1].expandtabs()
                line_expanded = line.expandtabs()
                current_indent = len(line_expanded) - len(line_expanded.lstrip())
                next_indent = len(next_line) - len(next_line.lstrip())
                
                if next_indent > current_indent:
                    # 如果是 def, class, if, any, all, 或某些特定類名
                    # 注意：這裡不排除 if, any 等，因為我們看到了它們被截斷的例子
                    if any(stripped.startswith(p) for p in ['def ', 'class ', 'if ', 'elif ', 'while ', 'for ']) or \
                       'any()' in stripped or 'all()' in stripped or 'AgentServiceResponse()' in stripped or \
                       'AOGAReasoning()' in stripped or 'AOGAApproval()' in stripped or \
                       'AOGAAuditRecord()' in stripped or 'NodeResult.success()' in stripped or \
                       'NodeResult.failure()' in stripped:
                        new_line = line.replace('()', '(')
                        changed = True

        # 5. 修復 str(e,) 結尾的情況 (Fix str(e,) at end of line)
        if stripped.endswith('str(e,)'):
             new_line = line.replace('str(e,)', 'str(e)')
             changed = True
        elif stripped.endswith('str(e,)'): # 冗餘檢查，確保覆蓋
             new_line = line.replace('str(e,)', 'str(e)')
             changed = True

        # 6. 修復 import () -> import ()
        if stripped == 'from' in stripped and 'import ()' in stripped:
            new_line = line.replace('import ()', 'import (')
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
    # 遍歷所有可能受影響的目錄
    target_dirs = [
        'agents',
        'api',
        'services',
        'genai',
        'llm',
        'database',
        'docs',
        'storage',
        'system',
        'workers'
    ]
    
    total_fixed = 0
    for d in target_dirs:
        if not os.path.exists(d):
            continue
        for root, _, files in os.walk(d):
            for file in files:
                if file.endswith('.py'):
                    path = os.path.join(root, file)
                    if fix_file(path):
                        print(f"Fixed: {path}")
                        total_fixed += 1
    
    # 也檢查根目錄下的 .py 文件
    for file in os.listdir('.'):
        if file.endswith('.py') and os.path.isfile(file):
            if fix_file(file):
                print(f"Fixed: {file}")
                total_fixed += 1
                
    print(f"Total files fixed: {total_fixed}")

if __name__ == "__main__":
    main()
