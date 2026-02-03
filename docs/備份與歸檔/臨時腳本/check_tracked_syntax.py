import os
import subprocess
import sys
from pathlib import Path

def get_tracked_files():
    result = subprocess.run(['git', 'ls-files'], capture_output=True, text=True)
    if result.returncode != 0:
        return []
    return [f for f in result.stdout.splitlines() if f.endswith('.py')]

def check_syntax(file_path):
    try:
        subprocess.run([sys.executable, '-m', 'py_compile', file_path], check=True, capture_output=True)
        return True, ""
    except subprocess.CalledProcessError as e:
        return False, e.stderr.decode()

def main():
    tracked_files = get_tracked_files()
    errors = []
    for f in tracked_files:
        success, err_msg = check_syntax(f)
        if not success:
            errors.append((f, err_msg))
    
    if not errors:
        print("No syntax errors found in tracked files.")
    else:
        print(f"Found {len(errors)} tracked files with syntax errors:")
        for f, msg in errors:
            print(f"--- {f} ---")
            print(msg)

if __name__ == "__main__":
    main()
