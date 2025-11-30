# 代碼功能說明: AutoGen Smoke Test
# 創建日期: 2025-10-25
# 創建人: Daniel Chung
# 最後修改日期: 2025-10-26

"""驗證 AutoGen 基礎功能和版本相容性。"""

import sys
from pathlib import Path

# 添加項目根目錄到路徑
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))


def test_pyautogen_version():
    """測試 pyautogen 版本。"""
    try:
        import pyautogen

        version = pyautogen.__version__
        print(f"✓ pyautogen 版本: {version}")

        # 檢查版本範圍
        major, minor = map(int, version.split(".")[:2])
        if major == 0 and minor >= 2:
            print("✓ 版本符合要求 (>=0.2.0, <0.3.0)")
            return True
        else:
            print(f"⚠ 版本可能不兼容 (當前: {version}, 期望: >=0.2.0, <0.3.0)")
            return False
    except ImportError as exc:
        print(f"✗ pyautogen 導入失敗: {exc}")
        return False
    except Exception as exc:
        print(f"✗ 版本檢查失敗: {exc}")
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
        return True
    except Exception as exc:
        print(f"✗ 配置載入失敗: {exc}")
        import traceback

        traceback.print_exc()
        return False


def test_agent_roles():
    """測試 Agent 角色定義。"""
    try:
        from agents.autogen.agent_roles import get_default_agent_roles

        roles = get_default_agent_roles()
        print("✓ Agent 角色定義成功")
        print(f"  - 角色數量: {len(roles)}")
        for role_name in roles.keys():
            print(f"  - {role_name}")
        return True
    except Exception as exc:
        print(f"✗ Agent 角色定義失敗: {exc}")
        return False


def test_workflow_factory():
    """測試 Workflow Factory。"""
    try:
        from agents.autogen.factory import AutoGenWorkflowFactory
        from agents.workflows.base import WorkflowRequestContext

        factory = AutoGenWorkflowFactory()
        print("✓ Workflow Factory 創建成功")

        # 測試構建 workflow
        ctx = WorkflowRequestContext(
            task_id="test-task-001",
            task="測試任務",
        )
        workflow = factory.build_workflow(ctx)
        print("✓ Workflow 構建成功")
        print(f"  - task_id: {workflow._ctx.task_id}")
        return True
    except Exception as exc:
        print(f"✗ Workflow Factory 測試失敗: {exc}")
        import traceback

        traceback.print_exc()
        return False


def test_factory_router():
    """測試 Factory Router 註冊。"""
    try:
        from agents.workflows.factory_router import get_workflow_factory_router
        from agents.task_analyzer.models import WorkflowType

        router = get_workflow_factory_router()
        factory = router.get_factory(WorkflowType.AUTOGEN)

        if factory:
            print("✓ AutoGen Factory 已註冊到 Router")
            return True
        else:
            print("✗ AutoGen Factory 未註冊到 Router")
            return False
    except Exception as exc:
        print(f"✗ Factory Router 測試失敗: {exc}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """主函數。"""
    print("=" * 60)
    print("AutoGen Smoke Test")
    print("=" * 60)

    results = []

    print("\n1. 測試 pyautogen 版本...")
    results.append(test_pyautogen_version())

    print("\n2. 測試配置載入...")
    results.append(test_config_loading())

    print("\n3. 測試 Agent 角色定義...")
    results.append(test_agent_roles())

    print("\n4. 測試 Workflow Factory...")
    results.append(test_workflow_factory())

    print("\n5. 測試 Factory Router...")
    results.append(test_factory_router())

    print("\n" + "=" * 60)
    if all(results):
        print("✓ 所有 Smoke Test 通過！")
        return 0
    else:
        print("✗ 部分 Smoke Test 失敗，請檢查上述錯誤信息")
        return 1


if __name__ == "__main__":
    sys.exit(main())
