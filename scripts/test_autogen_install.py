# 代碼功能說明: AutoGen 安裝驗證腳本
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""驗證 AutoGen 安裝和基礎配置。"""

import sys
from pathlib import Path

# 添加項目根目錄到路徑
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


def test_pyautogen_import():
    """測試 pyautogen 導入。"""
    try:
        import pyautogen

        print(f"✓ pyautogen 導入成功，版本: {pyautogen.__version__}")
        return True
    except ImportError as exc:
        print(f"✗ pyautogen 導入失敗: {exc}")
        return False


def test_config_loading():
    """測試配置載入。"""
    try:
        from agents.autogen.config import load_autogen_settings

        settings = load_autogen_settings()
        print("✓ 配置載入成功")
        print(f"  - enable_planning: {settings.enable_planning}")
        print(f"  - max_steps: {settings.max_steps}")
        print(f"  - default_llm: {settings.default_llm}")
        print(f"  - checkpoint_dir: {settings.checkpoint_dir}")
        return True
    except Exception as exc:
        print(f"✗ 配置載入失敗: {exc}")
        return False


def test_llm_adapter():
    """測試 LLM 適配器初始化。"""
    try:
        from agents.autogen.llm_adapter import AutoGenLLMAdapter

        adapter = AutoGenLLMAdapter(model_name="gpt-oss:20b")
        print("✓ LLM 適配器初始化成功")
        print(f"  - model_name: {adapter.model_name}")
        print(f"  - base_url: {adapter._base_url}")
        return True
    except Exception as exc:
        print(f"✗ LLM 適配器初始化失敗: {exc}")
        return False


def test_directory_structure():
    """測試目錄結構。"""
    try:
        autogen_dir = project_root / "agents" / "autogen"
        checkpoint_dir = project_root / "datasets" / "autogen" / "checkpoints"

        checks = [
            (autogen_dir, "agents/autogen"),
            (checkpoint_dir, "datasets/autogen/checkpoints"),
        ]

        all_ok = True
        for path, name in checks:
            if path.exists():
                print(f"✓ {name} 目錄存在")
            else:
                print(f"✗ {name} 目錄不存在")
                all_ok = False

        return all_ok
    except Exception as exc:
        print(f"✗ 目錄結構檢查失敗: {exc}")
        return False


def main():
    """主函數。"""
    print("=" * 60)
    print("AutoGen 安裝驗證")
    print("=" * 60)

    results = []

    print("\n1. 測試 pyautogen 導入...")
    results.append(test_pyautogen_import())

    print("\n2. 測試配置載入...")
    results.append(test_config_loading())

    print("\n3. 測試 LLM 適配器...")
    results.append(test_llm_adapter())

    print("\n4. 測試目錄結構...")
    results.append(test_directory_structure())

    print("\n" + "=" * 60)
    if all(results):
        print("✓ 所有測試通過！")
        return 0
    else:
        print("✗ 部分測試失敗，請檢查上述錯誤信息")
        return 1


if __name__ == "__main__":
    sys.exit(main())
