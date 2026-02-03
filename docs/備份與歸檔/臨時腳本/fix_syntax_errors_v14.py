# 代碼功能說明: 批量修復語法錯誤 (v14)
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
        if '(' in line and line.count('(') > line.count(')'):
             if i + 1 < len(lines):
                 next_line = lines[i+1].expandtabs()
                 line_expanded = line.expandtabs()
                 current_indent = len(line_expanded) - len(line_expanded.lstrip())
                 next_line_stripped = next_line.strip()
                 next_indent = len(next_line) - len(next_line.lstrip())
                 
                 if next_line_stripped and next_indent <= current_indent:
                     is_new_stmt = re.match(r'^[a-zA-Z_][a-zA-Z0-9_.]*\s*=', next_line_stripped) or \
                                   any(next_line_stripped.startswith(p) for p in ['self.', 'return ', 'if ', 'for ', 'while ', 'yield ', 'break', 'continue', 'logger.', 'print(', 'await ', 'raise ', 'async ', 'def ', 'class ', 'try:', 'except ', 'finally:']) or \
                                   next_line_stripped.startswith('#') or next_line_stripped.startswith('}') or next_line_stripped.startswith(']')
                     
                     if is_new_stmt:
                          if not stripped.endswith(':') and not stripped.endswith(',') and not stripped.endswith('\\'):
                               missing = line.count('(') - line.count(')')
                               new_line = line.rstrip() + (')' * missing)
                               changed = True

        # 3. 修復字典中遺漏的逗號 (Expected `,`, found string/name)
        if (stripped.endswith('"') or stripped.endswith("'") or stripped.endswith('}') or stripped.endswith(']') or stripped.endswith(')')) and \
           not stripped.endswith(',') and not stripped.endswith(':') and not stripped.endswith('\\'):
            if i + 1 < len(lines):
                next_line_stripped = lines[i+1].strip()
                if next_line_stripped.startswith('"') or next_line_stripped.startswith("'") or \
                   re.match(r'^[a-zA-Z_][a-zA-Z0-9_.]*\s*:', next_line_stripped):
                    new_line = line.rstrip() + ','
                    changed = True

        # 4. 修復 f-string 中遺漏的反括號 (e.g. ({mode}: -> ({mode}):)
        if 'f"' in line and '(' in line and '{' in line:
            # 尋找 ({...} 但沒有 )
            # 這裡只處理簡單的 ({var} 模式
            temp_line = re.sub(r'\(\{([a-zA-Z0-9_]+)\}', r'(\1)', new_line)
            # 或者更通用的：如果 f-string 中有 ( 且其後有 { 但在下一個 : 或 } 前沒有 )
            # 這裡比較難用正則，我們先處理明確的錯誤
            new_line = new_line.replace('({mode}:', '({mode}):').replace('({mode}:', '({mode}):')
            if new_line != line:
                changed = True

        # 5. 修復單獨一行的逗號應該是 ), 的情況
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
