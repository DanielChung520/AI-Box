import os
import re


def fix_structlog(file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace import
    new_content = content.replace("import structlog", "import logging")

    # Replace logger initialization
    new_content = re.sub(
        r"(self\._logger|self\.logger|logger)\s*=\s*structlog\.get_logger\([^)]*\)",
        r"\1 = logging.getLogger(__name__)",
        new_content,
    )

    # Remove .bind() and .with_fields() calls on loggers
    new_content = re.sub(r"\.bind\([^)]*\)", "", new_content)
    new_content = re.sub(r"\.with_fields\([^)]*\)", "", new_content)

    # Replace logger calls with f-strings
    levels = ["info", "debug", "error", "warning", "warn", "critical", "exception"]

    for level in levels:
        # Pattern: logger.info("msg", key=value, ...)
        pattern = (
            r"(self\._logger|self\.logger|logger)\."
            + level
            + r'\(\s*("[^"]*"|\'[^\']*\')\s*,\s*([^)]+)\)'
        )

        def replace_args(match):
            prefix = match.group(1)
            msg = match.group(2)
            args_str = match.group(3)

            if args_str.strip() == "exc_info=True":
                return f"{prefix}.{level}({msg}, exc_info=True)"

            # Simple parsing of key=value pairs
            kv_pairs = re.findall(r"(\w+)\s*=\s*([^,]+)", args_str)
            if kv_pairs:
                std_kwargs = ["exc_info", "stack_info", "stacklevel", "extra"]
                custom_kvs = [f"{k}={{ {v} }}" for k, v in kv_pairs if k not in std_kwargs]
                std_kvs = [f"{k}={v}" for k, v in kv_pairs if k in std_kwargs]

                new_msg = f'f"{msg[1:-1]}: ' + ", ".join(custom_kvs) + '"'
                if std_kvs:
                    return f"{prefix}.{level}({new_msg}, {', '.join(std_kvs)}")"
                else:
                    return f"{prefix}.{level}({new_msg)}"

            return match.group(0)

        new_content = re.sub(pattern, replace_args, new_content)

    if content != new_content:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    return False


def main():
    count = 0
    for root, dirs, files in os.walk("."):
        # EXCLUDE VENV AND OTHER NON-PROJECT DIRS
        if any(d in root for d in ["node_modules", ".git", "__pycache__", "venv", "env"]):
            continue
        for file in files:
            if file.endswith(".py"):
                if fix_structlog(os.path.join(root, file)):
                    count += 1
                    print(f"Fixed: {os.path.join(root, file)}")")
    print(f"Total files fixed: {count}")


if __name__ == "__main__":
    main()
