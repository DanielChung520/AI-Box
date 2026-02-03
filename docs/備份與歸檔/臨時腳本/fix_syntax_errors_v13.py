# 代碼功能說明: 批量修復語法錯誤 (v13)
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

        # 1. 修復錯誤的 super(.__init__(
        if 'super(.__init__(' in line:
            new_line = line.replace('super(.__init__(', 'super().__init__(')
            changed = True

        # 2. 修復未閉合的括號 (Next line is same or less indent)
        # 優化：增加更多觸發條件
        if '(' in line and line.count('(') > line.count(')'):
             if i + 1 < len(lines):
                 next_line = lines[i+1].expandtabs()
                 line_expanded = line.expandtabs()
                 current_indent = len(line_expanded) - len(line_expanded.lstrip())
                 next_line_stripped = next_line.strip()
                 next_indent = len(next_line) - len(next_line.lstrip())
                 
                 if next_line_stripped and next_indent <= current_indent:
                     # 如果下一行看起來像是一個新的賦值或語句
                     is_new_stmt = re.match(r'^[a-zA-Z_][a-zA-Z0-9_.]*\s*=', next_line_stripped) or \
                                   any(next_line_stripped.startswith(p) for p in ['self.', 'return ', 'if ', 'for ', 'while ', 'yield ', 'break', 'continue', 'logger.', 'print(', 'await ', 'raise ', 'async ', 'def ', 'class ', 'try:', 'except ', 'finally:']) or \
                                   next_line_stripped.startswith('#')
                     
                     if is_new_stmt:
                          if not stripped.endswith(':') and not stripped.endswith(','):
                               # 補齊所有缺少的括號
                               missing = line.count('(') - line.count(')')
                               new_line = line.rstrip() + (')' * missing)
                               changed = True

        # 3. 修復單獨一行的逗號應該是 ), 的情況
        if stripped == ',':
            if i > 0:
                prev_line = lines[i-1].strip()
                if any(prev_line.endswith(c) for c in ['"', "'", ']', '}', ')', ',', 'True', 'False', 'None']):
                    if i + 1 < len(lines):
                        next_line = lines[i+1].strip()
                        if '=' in next_line or any(next_line.startswith(c) for c in [')', ']', '}']) or \
                           any(p in next_line for p in ['PlanStep(', 'AOGAReasoning(', 'AOGAApproval(']):
                            new_line = line.replace(',', '),')
                            changed = True

        # 4. 修復 f-string 中的 {var)}
        if '{' in new_line and ')}' in new_line:
            new_line = re.sub(r'\{([a-zA-Z_][a-zA-Z0-9_.]*(?:\(\))?)\)\}', r'{\1}', new_line)
            if new_line != line:
                changed = True

        # 5. 修復字典中的 key: val)}
        if ')}' in new_line and ':' in new_line and not new_line.strip().startswith('f"'):
             new_line = re.sub(r':\s*([a-zA-Z_][a-zA-Z0-9_.]*)\)\}', r': \1}', new_line)
             if new_line != line:
                 changed = True
        
        # 6. 修復行尾多餘的引號
        if line.count('f"') >= 1 and stripped.endswith('")"'):
            new_line = line.rstrip()[:-1]
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
    print(f"Total files fixed: {total_fixed}")

if __name__ == "__main__":
    main()
