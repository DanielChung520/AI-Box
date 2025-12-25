# 代碼功能說明: 代碼管制表生成腳本
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""
代碼管制表生成腳本

掃描所有 Python 和 TypeScript 程式檔案，提取信息並生成代碼管制表。

用法:
    python generate_code_registry.py

輸出:
    docs/代碼管制表.md
"""

import re
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# 項目根目錄
PROJECT_ROOT = Path(__file__).parent

# 排除的目錄
EXCLUDED_DIRS = {
    "venv",
    "__pycache__",
    "node_modules",
    ".git",
    "backup",
    "htmlcov",
    "dist",
    "dev-dist",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".idea",
    ".vscode",
    "chroma_data",
    "logs",
}

# 排除的檔案模式
EXCLUDED_PATTERNS = [
    r"\.pyc$",
    r"\.pyo$",
    r"\.pyd$",
    r"\.so$",
    r"\.egg$",
]

# 模組分類映射
MODULE_MAPPING = {
    "api/": "API層",
    "services/": "服務層",
    "agents/": "Agent層",
    "genai/": "GenAI層",
    "database/": "數據庫層",
    "llm/": "LLM層",
    "mcp/": "MCP層",
    "system/": "系統層",
    "storage/": "存儲層",
    "workers/": "工作進程",
    "ai-bot/src/": "前端",
    "scripts/": "腳本",
    "tests/": "測試",
    "kag/": "知識圖譜",
}

# 模組編號前綴
MODULE_PREFIX = {
    "API層": "API",
    "服務層": "SRV",
    "Agent層": "AGT",
    "GenAI層": "GEN",
    "數據庫層": "DB",
    "LLM層": "LLM",
    "MCP層": "MCP",
    "系統層": "SYS",
    "存儲層": "STG",
    "工作進程": "WRK",
    "前端": "FRONT",
    "腳本": "SCRIPT",
    "測試": "TEST",
    "知識圖譜": "KAG",
    "其他": "OTH",
}


class CodeRegistryGenerator:
    """代碼管制表生成器"""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.files: List[Dict] = []

    def should_exclude_file(self, file_path: Path) -> bool:
        """檢查檔案是否應該被排除"""
        # 檢查目錄
        for part in file_path.parts:
            if part in EXCLUDED_DIRS:
                return True

        # 檢查檔案模式
        for pattern in EXCLUDED_PATTERNS:
            if re.search(pattern, str(file_path)):
                return True

        return False

    def find_code_files(self) -> List[Path]:
        """查找所有程式檔案"""
        code_files: List[Path] = []

        # 查找 Python 檔案
        for py_file in self.project_root.rglob("*.py"):
            if not self.should_exclude_file(py_file):
                code_files.append(py_file)

        # 查找 TypeScript 檔案
        for ts_file in self.project_root.rglob("*.ts"):
            if not self.should_exclude_file(ts_file):
                code_files.append(ts_file)

        # 查找 TSX 檔案
        for tsx_file in self.project_root.rglob("*.tsx"):
            if not self.should_exclude_file(tsx_file):
                code_files.append(tsx_file)

        return sorted(code_files)

    def get_module_name(self, file_path: Path) -> str:
        """根據檔案路徑識別功能模組"""
        relative_path = file_path.relative_to(self.project_root)
        path_str = str(relative_path).replace("\\", "/")

        for prefix, module_name in MODULE_MAPPING.items():
            if path_str.startswith(prefix):
                return module_name

        # 默認分類
        return "其他"

    def extract_header_info(self, file_path: Path) -> Dict[str, Optional[str]]:
        """從檔案頭部註釋提取信息"""
        info: Dict[str, Optional[str]] = {
            "description": None,
            "created_date": None,
            "last_modified_date": None,
            "creator": None,
        }

        try:
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()

            # 只檢查前 50 行
            for i, line in enumerate(lines[:50]):
                line = line.strip()

                # 提取功能描述
                if "功能說明" in line or "功能描述" in line or "代碼功能說明" in line:
                    # 嘗試提取冒號後面的內容
                    match = re.search(r"[：:]\s*(.+)", line)
                    if match:
                        info["description"] = match.group(1).strip()
                    # 如果下一行有內容，也嘗試提取
                    if i + 1 < len(lines) and lines[i + 1].strip():
                        next_line = lines[i + 1].strip()
                        if not next_line.startswith("#") and not next_line.startswith("//"):
                            info["description"] = next_line.strip()

                # 提取創建日期
                if "創建日期" in line:
                    match = re.search(r"[：:]\s*(\d{4}-\d{2}-\d{2})", line)
                    if match:
                        info["created_date"] = match.group(1)

                # 提取最後修改日期
                if "最後修改日期" in line or "最後更新日期" in line:
                    match = re.search(
                        r"[：:]\s*(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?(?:\s+\(UTC\+8\))?)",
                        line,
                    )
                    if match:
                        date_str = match.group(1).strip()
                        # 提取日期部分
                        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", date_str)
                        if date_match:
                            info["last_modified_date"] = date_match.group(1)

                # 提取創建人
                if "創建人" in line:
                    match = re.search(r"[：:]\s*(.+)", line)
                    if match:
                        info["creator"] = match.group(1).strip()

                # 從 docstring 提取描述（如果沒有找到其他描述）
                if i == 0 and line.startswith('"""') and not info["description"]:
                    # 嘗試提取 docstring 的第一行
                    docstring = line.strip("\"'")
                    if docstring and len(docstring) > 3:
                        info["description"] = docstring.strip()

        except Exception as e:
            print(f"⚠️  讀取檔案失敗 {file_path}: {e}", file=sys.stderr)

        return info

    def get_git_creation_date(self, file_path: Path) -> Optional[str]:
        """從 Git 歷史獲取檔案創建日期"""
        try:
            relative_path = file_path.relative_to(self.project_root)
            result = subprocess.run(
                [
                    "git",
                    "log",
                    "--diff-filter=A",
                    "--follow",
                    "--format=%ai",
                    "--",
                    str(relative_path),
                ],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0 and result.stdout:
                dates = result.stdout.strip().split("\n")
                if dates:
                    # 取最後一行（最早的提交）
                    last_date = dates[-1].strip()
                    # 提取日期部分
                    date_match = re.search(r"(\d{4}-\d{2}-\d{2})", last_date)
                    if date_match:
                        return date_match.group(1)

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass

        return None

    def get_git_last_modified_date(self, file_path: Path) -> Optional[str]:
        """從 Git 歷史獲取檔案最後修改日期"""
        try:
            relative_path = file_path.relative_to(self.project_root)
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ai", "--", str(relative_path)],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0 and result.stdout:
                date_str = result.stdout.strip()
                date_match = re.search(r"(\d{4}-\d{2}-\d{2})", date_str)
                if date_match:
                    return date_match.group(1)

        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, FileNotFoundError):
            pass

        return None

    def process_files(self) -> None:
        """處理所有檔案並提取信息"""
        print("🔍 掃描程式檔案...")
        code_files = self.find_code_files()
        total = len(code_files)
        print(f"📁 找到 {total} 個程式檔案\n")

        for idx, file_path in enumerate(code_files, 1):
            if idx % 50 == 0:
                print(f"⏳ 處理進度: {idx}/{total} ({idx*100//total}%)")

            relative_path = file_path.relative_to(self.project_root)
            module_name = self.get_module_name(file_path)

            # 提取檔案頭部信息
            header_info = self.extract_header_info(file_path)

            # 獲取 Git 日期（優先）
            git_created = self.get_git_creation_date(file_path)
            git_modified = self.get_git_last_modified_date(file_path)

            # 確定日期（優先使用 Git）
            created_date = git_created or header_info["created_date"] or "未知"
            last_modified_date = git_modified or header_info["last_modified_date"] or "未知"

            # 組裝備註
            notes_parts = []
            if header_info["creator"]:
                notes_parts.append(f"創建人: {header_info['creator']}")
            if git_created or git_modified:
                notes_parts.append("(Git歷史)")

            notes = "; ".join(notes_parts) if notes_parts else "-"

            # 功能描述
            description = header_info["description"] or "未提供功能描述"

            self.files.append(
                {
                    "module": module_name,
                    "name": file_path.name,
                    "path": str(relative_path).replace("\\", "/"),
                    "description": description,
                    "created_date": created_date,
                    "last_modified_date": last_modified_date,
                    "notes": notes,
                }
            )

        print(f"✅ 處理完成: {total} 個檔案\n")

    def generate_registry(self) -> str:
        """生成代碼管制表 Markdown"""
        # 按模組分組
        modules: Dict[str, List[Dict]] = defaultdict(list)
        for file_info in self.files:
            modules[file_info["module"]].append(file_info)

        # 生成編號
        registry_lines: List[str] = []
        registry_lines.append("# AI-Box 代碼管制表\n\n")
        registry_lines.append(f"**生成時間**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        registry_lines.append(f"**總檔案數**: {len(self.files)}\n\n")
        registry_lines.append("---\n\n")

        # 表格標題
        registry_lines.append("| 功能模組 | 編號 | 名稱 | 代碼 | 代碼功能描述 | 創建日期 | 最後更新日期 | 備註 |\n")
        registry_lines.append(
            "|---------|------|------|------|-------------|---------|-------------|------|\n"
        )

        # 按模組順序排列
        module_order = [
            "API層",
            "服務層",
            "Agent層",
            "GenAI層",
            "數據庫層",
            "LLM層",
            "MCP層",
            "系統層",
            "存儲層",
            "工作進程",
            "前端",
            "腳本",
            "知識圖譜",
            "測試",
            "其他",
        ]

        for module_name in module_order:
            if module_name not in modules:
                continue

            files = sorted(modules[module_name], key=lambda x: x["path"])
            module_prefix = MODULE_PREFIX.get(module_name, "UNK")

            for idx, file_info in enumerate(files, 1):
                code_number = f"{module_prefix}-{idx:03d}"

                # 轉義 Markdown 特殊字符
                def escape_md(text: str) -> str:
                    return text.replace("|", "\\|").replace("\n", " ").replace("\r", "")

                registry_lines.append(
                    f"| {module_name} | {code_number} | {escape_md(file_info['name'])} | "
                    f"`{file_info['path']}` | {escape_md(file_info['description'])} | "
                    f"{file_info['created_date']} | {file_info['last_modified_date']} | "
                    f"{escape_md(file_info['notes'])} |\n"
                )

        # 添加統計信息
        registry_lines.append("\n---\n\n")
        registry_lines.append("## 統計信息\n\n")
        registry_lines.append("| 功能模組 | 檔案數量 |\n")
        registry_lines.append("|---------|----------|\n")

        for module_name in module_order:
            if module_name in modules:
                count = len(modules[module_name])
                registry_lines.append(f"| {module_name} | {count} |\n")

        return "".join(registry_lines)

    def save_registry(self, output_path: Path) -> None:
        """保存代碼管制表"""
        print("📝 生成代碼管制表...")
        registry_content = self.generate_registry()

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(registry_content)

        print(f"✅ 代碼管制表已保存至: {output_path}")


def main():
    """主函數"""
    generator = CodeRegistryGenerator(PROJECT_ROOT)

    print("=" * 60)
    print("代碼管制表生成器")
    print("=" * 60)
    print()

    # 處理檔案
    generator.process_files()

    # 生成並保存
    output_path = PROJECT_ROOT / "docs" / "代碼管制表.md"
    generator.save_registry(output_path)

    print()
    print("=" * 60)
    print("✅ 完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
