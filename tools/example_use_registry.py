# 代碼功能說明: 工具註冊清單使用示例
# 創建日期: 2025-12-30
# 創建人: Daniel Chung
# 最後修改日期: 2025-12-30

"""工具註冊清單使用示例

展示如何使用工具註冊清單進行 AI 任務分析。
"""

from tools.registry_loader import (
    get_tool_info,
    get_tools_by_category,
    get_tools_for_task_analysis,
    list_all_tools,
    search_tools,
)


def example_1_list_all_tools():
    """示例 1: 列出所有工具"""
    print("=" * 60)
    print("示例 1: 列出所有工具")
    print("=" * 60)

    tools = list_all_tools()
    print(f"\n工具總數: {len(tools)}\n")

    for tool in tools:
        print(f"- {tool['name']} ({tool['category']})")
        print(f"  描述: {tool['description']}")
        print(f"  用途: {tool['purpose']}")
        print()


def example_2_get_tool_info():
    """示例 2: 獲取單個工具信息"""
    print("=" * 60)
    print("示例 2: 獲取 datetime 工具詳細信息")
    print("=" * 60)

    tool_info = get_tool_info("datetime")
    if tool_info:
        print(f"\n工具名稱: {tool_info['name']}")
        print(f"版本: {tool_info['version']}")
        print(f"類別: {tool_info['category']}")
        print(f"描述: {tool_info['description']}")
        print(f"用途: {tool_info['purpose']}")
        print("\n使用場景:")
        for use_case in tool_info["use_cases"]:
            print(f"  - {use_case}")
        print("\n示例場景:")
        for scenario in tool_info["example_scenarios"]:
            print(f"  - {scenario}")
    else:
        print("工具不存在")


def example_3_search_tools():
    """示例 3: 搜索工具"""
    print("=" * 60)
    print("示例 3: 搜索與「天氣」相關的工具")
    print("=" * 60)

    results = search_tools("天氣")
    print(f"\n找到 {len(results)} 個相關工具:\n")

    for tool in results:
        print(f"- {tool['name']} ({tool['category']})")
        print(f"  描述: {tool['description']}")
        print(f"  用途: {tool['purpose']}")
        print()


def example_4_get_tools_by_category():
    """示例 4: 根據類別獲取工具"""
    print("=" * 60)
    print("示例 4: 獲取所有「時間與日期」工具")
    print("=" * 60)

    time_tools = get_tools_by_category("時間與日期")
    print(f"\n找到 {len(time_tools)} 個時間工具:\n")

    for tool in time_tools:
        print(f"- {tool['name']}")
        print(f"  描述: {tool['description']}")
        print(f"  用途: {tool['purpose']}")
        print()


def example_5_ai_task_analysis():
    """示例 5: AI 任務分析使用"""
    print("=" * 60)
    print("示例 5: AI 任務分析 - 用戶詢問「現在幾點？」")
    print("=" * 60)

    # 模擬 AI 任務分析流程
    # user_query = "現在幾點？"  # 用於示例說明

    # 1. 搜索相關工具
    time_tools = search_tools("時間")
    print(f"\n1. 搜索到 {len(time_tools)} 個時間相關工具")

    # 2. 分析每個工具的用途和使用場景
    print("\n2. 分析工具用途和使用場景:")
    for tool in time_tools:
        print(f"\n工具: {tool['name']}")
        print(f"  用途: {tool['purpose']}")
        print("  使用場景:")
        for use_case in tool["use_cases"]:
            print(f"    - {use_case}")

    # 3. 選擇最合適的工具
    print("\n3. 選擇最合適的工具:")
    selected_tool = None
    for tool in time_tools:
        # 檢查示例場景是否匹配用戶查詢
        for scenario in tool.get("example_scenarios", []):
            if "現在幾點" in scenario or "當前時間" in scenario:
                selected_tool = tool
                break
        if selected_tool:
            break

    if selected_tool:
        print(f"\n選擇工具: {selected_tool['name']}")
        print(f"原因: {selected_tool['purpose']}")
        print("\n需要的參數:")
        for param_name, param_info in selected_tool.get("input_parameters", {}).items():
            required = param_info.get("required", False)
            print(
                f"  - {param_name}: {param_info.get('description', '')} {'(必填)' if required else '(可選)'}"
            )

        print("\n返回結果:")
        for field_name, field_desc in selected_tool.get("output_fields", {}).items():
            print(f"  - {field_name}: {field_desc}")


def example_6_get_analysis_format():
    """示例 6: 獲取用於 AI 分析的格式化清單"""
    print("=" * 60)
    print("示例 6: 獲取用於 AI 任務分析的格式化工具清單")
    print("=" * 60)

    analysis_tools = get_tools_for_task_analysis()
    print(f"\n版本: {analysis_tools['version']}")
    print(f"最後更新: {analysis_tools['last_updated']}")
    print(f"工具總數: {analysis_tools['total_count']}")

    print("\n工具列表（前 3 個）:")
    for tool in analysis_tools["tools"][:3]:
        print(f"\n- {tool['name']} ({tool['category']})")
        print(f"  用途: {tool['purpose']}")
        print(f"  使用場景: {', '.join(tool['use_cases'][:2])}...")


if __name__ == "__main__":
    example_1_list_all_tools()
    example_2_get_tool_info()
    example_3_search_tools()
    example_4_get_tools_by_category()
    example_5_ai_task_analysis()
    example_6_get_analysis_format()
