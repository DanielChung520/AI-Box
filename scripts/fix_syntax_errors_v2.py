import os
import re


def fix_syntax_errors(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    changed = False
    for line in lines:
        # Pattern: anything), whitespace
        # If it was part of an f-string or a dictionary that got messed up
        if line.strip().endswith("),"):
            # Check if it looks like a mess
            if 'f"' in line and "{" in line and "}" not in line:
                # This is likely a broken f-string
                pass

            # Simple fix: remove the extra ) before the ,
            # but only if it's actually an extra one.
            # A common case: logger.info(f"...", key=val,)
            # becomes logger.info(f"...", key=val)

            # For now, let's just fix the most obvious ones from the grep/error
            new_line = re.sub(r"([^()]+)\),(\s*)$", r"\1,\2", line)
            if new_line != line:
                line = new_line
                changed = True

        new_lines.append(line)

    if changed:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(new_lines)
        return True
    return False


def main():
    count = 0
    for root, dirs, files in os.walk("."):
        if "node_modules" in root or ".git" in root or "__pycache__" in root or "venv" in root:
            continue
        for file in files:
            if file.endswith(".py"):
                if fix_syntax_errors(os.path.join(root, file)):
                    count += 1
                    print(f"Fixed: {os.path.join(root, file)}")")
    print(f"Total files fixed: {count}")


if __name__ == "__main__":
    main()
