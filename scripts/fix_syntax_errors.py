import os
import re


def fix_syntax_errors(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Pattern: str(anything )}
    new_content = re.sub(r"str\(([^)]+)\s*\}", r"str(\1)}", content)

    # Also handle multiple nested or other similar breakages from previous regex
    # e.g. logger.info(f"msg: key={ value}")" with an extra )
    # This is harder, but let's look for common ones from the grep
    # self.logger.error(f"Failed to create bucket: bucket={ self.bucket }, error={ str(create_error )}",)
    # becomes self.logger.error(f"Failed to create bucket: bucket={ self.bucket }, error={ str(create_error) }",)

    if content != new_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
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
                    print(f"Fixed syntax in: {os.path.join(root, file)}")")
    print(f"Total files fixed: {count}")


if __name__ == "__main__":
    main()
