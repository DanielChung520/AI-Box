# 代碼功能說明: 檢查系統設計文檔中的文件引用路徑問題
# 創建日期: 2025-01-27
# 創建人: Daniel Chung
# 最後修改日期: 2025-01-27

"""
檢查系統設計文檔核心組件中的文件引用路徑問題

掃描所有核心組件文件，檢查：
1. 文件引用路徑是否存在
2. 是否有外部文件引用（非專案路徑）
3. 複製外部文件到參考文件目錄

用法:
    python check_docs_references.py
"""

import re
import shutil
import sys
from pathlib import Path
from typing import List, Set, Tuple
from urllib.parse import unquote

# 項目根目錄
PROJECT_ROOT = Path(__file__).parent

# 核心組件目錄
CORE_COMPONENTS_DIR = PROJECT_ROOT / "docs" / "系统设计文档" / "核心组件"

# 參考文件目錄
REF_FILES_DIR = PROJECT_ROOT / "docs" / "系统设计文档" / "參考文件"

# Markdown 鏈接正則表達式
MARKDOWN_LINK_PATTERN = re.compile(r"\[([^\]]+)\]\(([^\)]+)\)")

# 文件擴展名模式
FILE_EXT_PATTERN = re.compile(r"\.(md|html|pdf|docx|xlsx|png|jpg|jpeg|svg)$", re.IGNORECASE)


def is_external_path(path_str: str) -> bool:
    """
    判斷是否為外部路徑（非專案路徑）

    Args:
        path_str: 路徑字符串

    Returns:
        是否為外部路徑
    """
    # 移除 URL 解碼
    path_str = unquote(path_str)

    # 檢查是否為絕對路徑（以 / 或 ~ 開頭，但不是專案路徑）
    if path_str.startswith("/") or path_str.startswith("~"):
        # 檢查是否在專案目錄內
        abs_path = Path(path_str).expanduser().resolve()
        try:
            abs_path.relative_to(PROJECT_ROOT.resolve())
            return False  # 在專案內
        except ValueError:
            return True  # 在專案外

    # 檢查是否包含父目錄引用（../）且可能指向外部
    if path_str.startswith("../") and "../" * 3 in path_str:
        # 多層父目錄可能指向外部
        return True

    # 檢查是否為 HTTP/HTTPS 鏈接
    if path_str.startswith(("http://", "https://")):
        return False  # URL 鏈接，不需要複製

    return False


def resolve_path(link_path: str, base_file: Path) -> Path:
    """
    解析鏈接路徑為絕對路徑

    Args:
        link_path: 鏈接路徑
        base_file: 基礎文件路徑

    Returns:
        解析後的絕對路徑
    """
    # URL 解碼
    link_path = unquote(link_path)

    # 如果是絕對路徑
    if link_path.startswith("/") or link_path.startswith("~"):
        return Path(link_path).expanduser().resolve()

    # 如果是相對路徑，使用標準解析方法
    base_dir = base_file.parent.resolve()
    resolved = (base_dir / link_path).resolve()

    return resolved


def find_all_markdown_files(directory: Path) -> List[Path]:
    """
    查找所有 Markdown 文件

    Args:
        directory: 目錄路徑

    Returns:
        Markdown 文件列表
    """
    md_files = []
    for md_file in directory.rglob("*.md"):
        md_files.append(md_file)
    return sorted(md_files)


def extract_file_references(content: str) -> List[str]:
    """
    提取文件引用

    Args:
        content: 文件內容

    Returns:
        文件路徑列表
    """
    references: Set[str] = set()

    # 提取 Markdown 鏈接
    for match in MARKDOWN_LINK_PATTERN.finditer(content):
        link_path = match.group(2)
        # 跳過 URL 鏈接和錨點
        if not link_path.startswith(("http://", "https://", "#")):
            references.add(link_path)

    return sorted(references)


def check_references() -> Tuple[List[dict], List[dict]]:
    """
    檢查所有文件引用

    Returns:
        (問題列表, 外部文件列表)
    """
    print(f"📖 掃描核心組件目錄: {CORE_COMPONENTS_DIR}")
    md_files = find_all_markdown_files(CORE_COMPONENTS_DIR)
    print(f"✅ 找到 {len(md_files)} 個 Markdown 文件\n")

    problems: List[dict] = []
    external_files: List[dict] = []

    for md_file in md_files:
        print(f"🔍 檢查: {md_file.relative_to(PROJECT_ROOT)}")
        try:
            with open(md_file, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            print(f"  ❌ 無法讀取文件: {e}\n")
            continue

        references = extract_file_references(content)

        for ref_path in references:
            # 解析路徑
            resolved_path = resolve_path(ref_path, md_file)

            # 如果標準解析失敗，嘗試查找實際存在的文件
            if not resolved_path.exists():
                # 檢查是否是 Documents/Notion 路徑（需要向上4級到用戶目錄）
                if "Documents/Notion" in ref_path or "Documents/Notion" in str(resolved_path):
                    # 提取 Documents 之後的部分
                    parts = ref_path.split("Documents/")
                    if len(parts) > 1:
                        # 構建實際路徑：/Users/daniel/Documents/...
                        user_home = Path.home()  # /Users/daniel
                        actual_path = user_home.parent / "Documents" / parts[1]
                        # 如果路徑缺少擴展名，嘗試添加 .md
                        if not actual_path.exists() and not actual_path.suffix:
                            actual_path = actual_path.with_suffix(".md")
                        if actual_path.exists():
                            resolved_path = actual_path
                # 檢查是否是 開發過程文件（應該在 docs/ 目錄下）
                elif "開發過程文件" in ref_path:
                    file_name = Path(ref_path).name
                    possible_path = PROJECT_ROOT / "docs" / "開發過程文件" / file_name
                    if possible_path.exists():
                        resolved_path = possible_path

            # 檢查是否為外部路徑（在專案目錄外）
            try:
                resolved_path.relative_to(PROJECT_ROOT.resolve())
                is_external = False
            except ValueError:
                is_external = True

            # 檢查路徑是否存在
            if resolved_path.exists() and resolved_path.is_file():
                if is_external:
                    external_files.append(
                        {
                            "source_file": md_file.relative_to(PROJECT_ROOT),
                            "ref_path": ref_path,
                            "external_file": resolved_path,
                        }
                    )
                    print(f"  ⚠️  外部文件引用: {ref_path} -> {resolved_path}")
                else:
                    print(f"  ✓ 路徑有效: {ref_path}")
            else:
                if is_external:
                    problems.append(
                        {
                            "source_file": md_file.relative_to(PROJECT_ROOT),
                            "ref_path": ref_path,
                            "issue": f"外部路徑不存在: {resolved_path}",
                        }
                    )
                    print(f"  ❌ 外部路徑不存在: {ref_path}")
                else:
                    problems.append(
                        {
                            "source_file": md_file.relative_to(PROJECT_ROOT),
                            "ref_path": ref_path,
                            "issue": f"路徑不存在: {resolved_path}",
                        }
                    )
                    print(f"  ❌ 路徑不存在: {ref_path}")

        if not references:
            print("  ✓ 無文件引用")
        print()

    return problems, external_files


def copy_external_files(external_files: List[dict]) -> None:
    """
    複製外部文件到參考文件目錄

    Args:
        external_files: 外部文件列表
    """
    if not external_files:
        print("✅ 沒有外部文件需要複製\n")
        return

    # 創建參考文件目錄
    REF_FILES_DIR.mkdir(parents=True, exist_ok=True)

    print(f"📋 複製外部文件到: {REF_FILES_DIR}\n")

    copied_files = []
    for item in external_files:
        external_file = item["external_file"]
        ref_path = item["ref_path"]

        # 生成目標文件名（保持原始文件名）
        target_file = REF_FILES_DIR / external_file.name

        # 如果目標文件已存在，添加編號
        counter = 1
        original_target = target_file
        while target_file.exists():
            stem = original_target.stem
            suffix = original_target.suffix
            target_file = REF_FILES_DIR / f"{stem}_{counter}{suffix}"
            counter += 1

        try:
            shutil.copy2(external_file, target_file)
            copied_files.append(
                {
                    "source": external_file,
                    "target": target_file.relative_to(PROJECT_ROOT),
                    "original_ref": ref_path,
                }
            )
            print(f"  ✅ 已複製: {external_file.name} -> {target_file.relative_to(PROJECT_ROOT)}")
        except Exception as e:
            print(f"  ❌ 複製失敗: {external_file} -> {e}")

    print(f"\n📊 總共複製了 {len(copied_files)} 個外部文件")


def generate_report(problems: List[dict], external_files: List[dict]) -> None:
    """
    生成問題報告

    Args:
        problems: 問題列表
        external_files: 外部文件列表
    """
    report_file = PROJECT_ROOT / "docs" / "系统设计文档" / "文件引用檢查報告.md"

    with open(report_file, "w", encoding="utf-8") as f:
        f.write("# 系統設計文檔文件引用檢查報告\n\n")
        f.write("**生成時間**: 2025-01-27\n")
        f.write("**檢查範圍**: `docs/系统设计文档/核心组件/`\n\n")
        f.write("---\n\n")

        # 問題列表
        f.write("## ❌ 路徑問題列表\n\n")
        if problems:
            f.write(f"共發現 **{len(problems)}** 個問題：\n\n")
            f.write("| 來源文件 | 引用路徑 | 問題描述 |\n")
            f.write("|---------|---------|---------|\n")
            for prob in problems:
                source = str(prob["source_file"]).replace("|", "\\|")
                ref = prob["ref_path"].replace("|", "\\|")
                issue = prob["issue"].replace("|", "\\|")
                f.write(f"| `{source}` | `{ref}` | {issue} |\n")
        else:
            f.write("✅ 沒有發現路徑問題\n\n")
        f.write("\n---\n\n")

        # 外部文件列表
        f.write("## 📋 外部文件列表\n\n")
        if external_files:
            f.write(f"共發現 **{len(external_files)}** 個外部文件引用：\n\n")
            f.write("| 來源文件 | 原始引用路徑 | 外部文件路徑 |\n")
            f.write("|---------|-------------|-------------|\n")
            for ext in external_files:
                source = str(ext["source_file"]).replace("|", "\\|")
                ref = ext["ref_path"].replace("|", "\\|")
                ext_path = str(ext["external_file"]).replace("|", "\\|")
                f.write(f"| `{source}` | `{ref}` | `{ext_path}` |\n")
            f.write("\n**注意**: 這些外部文件已複製到 `docs/系统设计文档/參考文件/` 目錄\n\n")
        else:
            f.write("✅ 沒有發現外部文件引用\n\n")

    print(f"📄 檢查報告已生成: {report_file.relative_to(PROJECT_ROOT)}")


def main() -> None:
    """主函數"""
    print("🔄 開始檢查系統設計文檔中的文件引用路徑...\n")

    # 檢查目錄是否存在
    if not CORE_COMPONENTS_DIR.exists():
        print(f"❌ 錯誤: 核心組件目錄不存在: {CORE_COMPONENTS_DIR}")
        sys.exit(1)

    # 檢查引用
    problems, external_files = check_references()

    # 複製外部文件
    if external_files:
        print("=" * 60)
        copy_external_files(external_files)
        print("=" * 60)
        print()

    # 生成報告
    generate_report(problems, external_files)

    # 總結
    print("\n" + "=" * 60)
    print("📊 檢查總結")
    print("=" * 60)
    print(f"✅ 路徑問題: {len(problems)} 個")
    print(f"✅ 外部文件: {len(external_files)} 個")
    if problems:
        print("\n⚠️  請檢查報告文件了解詳細問題")
    if external_files:
        print("✅ 外部文件已複製到參考文件目錄")
    print("\n✨ 檢查完成！")


if __name__ == "__main__":
    main()
