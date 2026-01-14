# 代碼功能說明: Agent Display Config 數據遷移腳本
# 創建日期: 2026-01-13
# 創建人: Daniel Chung
# 最後修改日期: 2026-01-13

"""Agent Display Config 數據遷移腳本

將前端硬編碼的代理展示區配置遷移到 ArangoDB。
從 ChatArea.tsx 和 useLanguage.ts 提取數據並轉換為 ArangoDB 文檔格式。
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Dict

# 添加項目根目錄到 Python 路徑
base_dir = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(base_dir))

from dotenv import load_dotenv

# 顯式加載 .env 文件
env_path = base_dir / ".env"
load_dotenv(dotenv_path=env_path)

from services.api.models.agent_display_config import AgentConfig, CategoryConfig, MultilingualText
from services.api.services.agent_display_config_store_service import AgentDisplayConfigStoreService

# 從 ChatArea.tsx 提取的硬編碼數據
# 分類和代理的結構定義
CATEGORIES_DATA = [
    {
        "id": "human-resource",
        "display_order": 1,
        "agents": [
            {"id": "hr-1", "icon": "fa-user-tie", "status": "online", "usage_count": 124},
            {"id": "hr-2", "icon": "fa-graduation-cap", "status": "online", "usage_count": 87},
            {"id": "hr-3", "icon": "fa-chart-line", "status": "maintenance", "usage_count": 65},
            {"id": "hr-4", "icon": "fa-handshake", "status": "online", "usage_count": 92},
            {"id": "hr-5", "icon": "fa-coins", "status": "online", "usage_count": 78},
            {"id": "hr-6", "icon": "fa-seedling", "status": "online", "usage_count": 63},
        ],
    },
    {
        "id": "logistics",
        "display_order": 2,
        "agents": [
            {"id": "log-1", "icon": "fa-truck", "status": "online", "usage_count": 156},
            {"id": "log-2", "icon": "fa-warehouse", "status": "online", "usage_count": 98},
            {"id": "log-3", "icon": "fa-route", "status": "online", "usage_count": 129},
            {"id": "log-4", "icon": "fa-chart-bar", "status": "online", "usage_count": 85},
            {"id": "log-5", "icon": "fa-hand-holding-box", "status": "online", "usage_count": 76},
        ],
    },
    {
        "id": "finance",
        "display_order": 3,
        "agents": [
            {"id": "fin-1", "icon": "fa-chart-pie", "status": "online", "usage_count": 203},
            {
                "id": "fin-2",
                "icon": "fa-money-bill-wave",
                "status": "maintenance",
                "usage_count": 112,
            },
            {"id": "fin-3", "icon": "fa-piggy-bank", "status": "online", "usage_count": 157},
            {
                "id": "fin-4",
                "icon": "fa-file-invoice-dollar",
                "status": "online",
                "usage_count": 189,
            },
            {"id": "fin-5", "icon": "fa-receipt", "status": "maintenance", "usage_count": 67},
            {"id": "fin-6", "icon": "fa-chart-line", "status": "online", "usage_count": 134},
        ],
    },
    {
        "id": "mes",
        "display_order": 4,
        "agents": [
            {"id": "mes-1", "icon": "fa-industry", "status": "online", "usage_count": 256},
            {"id": "mes-2", "icon": "fa-check-circle", "status": "online", "usage_count": 143},
            {"id": "mes-3", "icon": "fa-tachometer-alt", "status": "online", "usage_count": 109},
            {"id": "mes-4", "icon": "fa-tools", "status": "online", "usage_count": 137},
            {"id": "mes-5", "icon": "fa-calendar-alt", "status": "online", "usage_count": 168},
            {"id": "mes-6", "icon": "fa-box-open", "status": "online", "usage_count": 95},
            {"id": "mes-7", "icon": "fa-sliders-h", "status": "online", "usage_count": 83},
        ],
    },
]

# 從 useLanguage.ts 提取的多語言翻譯數據
TRANSLATIONS: Dict[str, Dict[str, str]] = {
    # 分類名稱
    "agent.category.humanResource": {
        "en": "Human Resource",
        "zh_CN": "人力资源",
        "zh_TW": "人力資源",
    },
    "agent.category.logistics": {
        "en": "Logistics",
        "zh_CN": "物流",
        "zh_TW": "物流",
    },
    "agent.category.finance": {
        "en": "Finance",
        "zh_CN": "财务",
        "zh_TW": "財務",
    },
    "agent.category.mes": {
        "en": "MES",
        "zh_CN": "生产管理",
        "zh_TW": "生產管理",
    },
    # HR 代理名稱
    "agent.hr.assistant": {
        "en": "Assistant",
        "zh_CN": "助理",
        "zh_TW": "助理",
    },
    "agent.hr.trainingManager": {
        "en": "Training Manager",
        "zh_CN": "培训管理员",
        "zh_TW": "培訓管理員",
    },
    "agent.hr.performanceAnalysis": {
        "en": "Performance Analysis",
        "zh_CN": "绩效分析",
        "zh_TW": "績效分析",
    },
    "agent.hr.employeeRelations": {
        "en": "Employee Relations",
        "zh_CN": "员工关系",
        "zh_TW": "員工關係",
    },
    "agent.hr.compensationBenefits": {
        "en": "Compensation & Benefits",
        "zh_CN": "薪酬福利",
        "zh_TW": "薪酬福利",
    },
    "agent.hr.talentDevelopment": {
        "en": "Talent Development",
        "zh_CN": "人才发展",
        "zh_TW": "人才發展",
    },
    # HR 代理描述
    "agent.hr.description.assistant": {
        "en": "Intelligent resume screening, interview scheduling, recruitment report generation",
        "zh_CN": "智能筛选简历、安排面试、生成招聘报告",
        "zh_TW": "智能篩選簡歷、安排面試、生成招聘報告",
    },
    "agent.hr.description.trainingManager": {
        "en": "Design training courses, track learning progress, evaluate effectiveness",
        "zh_CN": "设计培训课程、跟踪学习进度、评估效果",
        "zh_TW": "設計培訓課程、跟蹤學習進度、評估效果",
    },
    "agent.hr.description.performanceAnalysis": {
        "en": "Automated performance evaluation, provide improvement suggestions, generate reports",
        "zh_CN": "自动化绩效评估、提供改进建议、生成报告",
        "zh_TW": "自動化績效評估、提供改進建議、生成報告",
    },
    "agent.hr.description.employeeRelations": {
        "en": "Handle employee inquiries, resolve conflicts, enhance team cohesion",
        "zh_CN": "处理员工咨询、解决冲突、提升团队凝聚力",
        "zh_TW": "處理員工諮詢、解決衝突、提升團隊凝聚力",
    },
    "agent.hr.description.compensationBenefits": {
        "en": "Analyze market compensation, design benefit plans, optimize incentive mechanisms",
        "zh_CN": "分析市场薪酬、设计福利方案、优化激励机制",
        "zh_TW": "分析市場薪酬、設計福利方案、優化激勵機制",
    },
    "agent.hr.description.talentDevelopment": {
        "en": "Identify high-potential talent, develop growth plans, build talent pipeline",
        "zh_CN": "识别高潜人才、制定发展计划、构建人才梯队",
        "zh_TW": "識別高潛人才、制定發展計劃、構建人才梯隊",
    },
    # Logistics 代理名稱
    "agent.logistics.supplyChainOptimization": {
        "en": "Supply Chain Optimization",
        "zh_CN": "供应链优化",
        "zh_TW": "供應鏈優化",
    },
    "agent.logistics.inventoryManagement": {
        "en": "Inventory Management",
        "zh_CN": "库存管理",
        "zh_TW": "庫存管理",
    },
    "agent.logistics.routePlanning": {
        "en": "Transport Route Planning",
        "zh_CN": "运输路线规划",
        "zh_TW": "運輸路線規劃",
    },
    "agent.logistics.dataAnalysis": {
        "en": "Logistics Data Analysis",
        "zh_CN": "物流数据分析",
        "zh_TW": "物流數據分析",
    },
    "agent.logistics.supplierManagement": {
        "en": "Supplier Management",
        "zh_CN": "供应商管理",
        "zh_TW": "供應商管理",
    },
    # Logistics 代理描述
    "agent.logistics.description.supplyChainOptimization": {
        "en": "Analyze supply chain data, provide optimization suggestions, predict demand",
        "zh_CN": "分析供应链数据、提供优化建议、预测需求",
        "zh_TW": "分析供應鏈數據、提供優化建議、預測需求",
    },
    "agent.logistics.description.inventoryManagement": {
        "en": "Monitor inventory levels, predict demand, generate replenishment suggestions",
        "zh_CN": "监控库存水平、预测需求、生成补货建议",
        "zh_TW": "監控庫存水平、預測需求、生成補貨建議",
    },
    "agent.logistics.description.routePlanning": {
        "en": "Optimize delivery routes, reduce transportation costs, improve delivery efficiency",
        "zh_CN": "优化配送路线、降低运输成本、提高配送效率",
        "zh_TW": "優化配送路線、降低運輸成本、提高配送效率",
    },
    "agent.logistics.description.dataAnalysis": {
        "en": "Analyze logistics performance, identify improvement points, generate data reports",
        "zh_CN": "分析物流绩效、识别改进点、生成数据报告",
        "zh_TW": "分析物流績效、識別改進點、生成數據報告",
    },
    "agent.logistics.description.supplierManagement": {
        "en": "Evaluate supplier performance, manage partnerships, optimize procurement processes",
        "zh_CN": "评估供应商绩效、管理合作关系、优化采购流程",
        "zh_TW": "評估供應商績效、管理合作關係、優化採購流程",
    },
    # Finance 代理名稱
    "agent.finance.financialAnalyst": {
        "en": "Financial Analyst",
        "zh_CN": "财务分析师",
        "zh_TW": "財務分析師",
    },
    "agent.finance.budgetPlanning": {
        "en": "Budget Planning",
        "zh_CN": "预算规划",
        "zh_TW": "預算規劃",
    },
    "agent.finance.costControl": {
        "en": "Cost Control",
        "zh_CN": "成本控制",
        "zh_TW": "成本控制",
    },
    "agent.finance.financialReportGeneration": {
        "en": "Financial Report Generation",
        "zh_CN": "财务报表生成",
        "zh_TW": "財務報表生成",
    },
    "agent.finance.taxPlanning": {
        "en": "Tax Planning",
        "zh_CN": "税务筹划",
        "zh_TW": "稅務籌劃",
    },
    "agent.finance.investmentAnalysis": {
        "en": "Investment Analysis",
        "zh_CN": "投资分析",
        "zh_TW": "投資分析",
    },
    # Finance 代理描述
    "agent.finance.description.financialAnalyst": {
        "en": "Analyze financial data, generate reports, provide decision support",
        "zh_CN": "分析财务数据、生成报表、提供决策支持",
        "zh_TW": "分析財務數據、生成報表、提供決策支持",
    },
    "agent.finance.description.budgetPlanning": {
        "en": "Assist in budget development, track expenses, forecast financial status",
        "zh_CN": "协助制定预算、跟踪支出、预测财务状况",
        "zh_TW": "協助制定預算、跟蹤支出、預測財務狀況",
    },
    "agent.finance.description.costControl": {
        "en": "Analyze cost structure, identify savings opportunities, optimize cost management",
        "zh_CN": "分析成本结构、识别节约机会、优化成本管理",
        "zh_TW": "分析成本結構、識別節約機會、優化成本管理",
    },
    "agent.finance.description.financialReportGeneration": {
        "en": "Automatically generate various financial reports, ensure data accuracy",
        "zh_CN": "自动化生成各类财务报表、确保数据准确性",
        "zh_TW": "自動化生成各類財務報表、確保數據準確性",
    },
    "agent.finance.description.taxPlanning": {
        "en": "Analyze tax policies, provide compliance advice, optimize tax structure",
        "zh_CN": "分析税务政策、提供合规建议、优化税务结构",
        "zh_TW": "分析稅務政策、提供合規建議、優化稅務結構",
    },
    "agent.finance.description.investmentAnalysis": {
        "en": "Evaluate investment projects, predict returns, provide investment advice",
        "zh_CN": "评估投资项目、预测回报、提供投资建议",
        "zh_TW": "評估投資項目、預測回報、提供投資建議",
    },
    # MES 代理名稱
    "agent.mes.productionMonitoring": {
        "en": "Production Monitoring",
        "zh_CN": "生产监控",
        "zh_TW": "生產監控",
    },
    "agent.mes.qualityControl": {
        "en": "Quality Control",
        "zh_CN": "质量控制",
        "zh_TW": "質量控制",
    },
    "agent.mes.efficiencyAnalysis": {
        "en": "Efficiency Analysis",
        "zh_CN": "效率分析",
        "zh_TW": "效率分析",
    },
    "agent.mes.equipmentMaintenance": {
        "en": "Equipment Maintenance",
        "zh_CN": "设备维护",
        "zh_TW": "設備維護",
    },
    "agent.mes.productionScheduling": {
        "en": "Production Scheduling",
        "zh_CN": "生产排程",
        "zh_TW": "生產排程",
    },
    "agent.mes.materialManagement": {
        "en": "Material Management",
        "zh_CN": "物料管理",
        "zh_TW": "物料管理",
    },
    "agent.mes.processOptimization": {
        "en": "Process Parameter Optimization",
        "zh_CN": "工艺参数优化",
        "zh_TW": "工藝參數優化",
    },
    # MES 代理描述
    "agent.mes.description.productionMonitoring": {
        "en": "Real-time monitoring of production processes, detect anomalies, provide alerts",
        "zh_CN": "实时监控生产流程、检测异常、提供预警",
        "zh_TW": "實時監控生產流程、檢測異常、提供預警",
    },
    "agent.mes.description.qualityControl": {
        "en": "Analyze quality data, identify issues, provide improvement suggestions",
        "zh_CN": "分析质量数据、识别问题、提供改进建议",
        "zh_TW": "分析質量數據、識別問題、提供改進建議",
    },
    "agent.mes.description.efficiencyAnalysis": {
        "en": "Evaluate production efficiency, identify bottlenecks, provide optimization solutions",
        "zh_CN": "评估生产效率、识别瓶颈、提供优化方案",
        "zh_TW": "評估生產效率、識別瓶頸、提供優化方案",
    },
    "agent.mes.description.equipmentMaintenance": {
        "en": "Predict equipment failures, develop maintenance plans, optimize equipment utilization",
        "zh_CN": "预测设备故障、制定维护计划、优化设备利用率",
        "zh_TW": "預測設備故障、制定維護計劃、優化設備利用率",
    },
    "agent.mes.description.productionScheduling": {
        "en": "Optimize production plans, arrange resources reasonably, improve on-time delivery rate",
        "zh_CN": "优化生产计划、合理安排资源、提高交付准时率",
        "zh_TW": "優化生產計劃、合理安排資源、提高交付準時率",
    },
    "agent.mes.description.materialManagement": {
        "en": "Track material usage, optimize material distribution, reduce inventory backlog",
        "zh_CN": "跟踪物料使用、优化物料配送、减少库存积压",
        "zh_TW": "跟蹤物料使用、優化物料配送、減少庫存積壓",
    },
    "agent.mes.description.processOptimization": {
        "en": "Analyze process data, optimize parameter settings, improve product quality",
        "zh_CN": "分析工艺数据、优化参数设置、提高产品质量",
        "zh_TW": "分析工藝數據、優化參數設置、提高產品質量",
    },
}

# 代理名稱翻譯鍵名映射（從 ChatArea.tsx 的邏輯提取）
# hr-1 的名稱是 category + assistant
AGENT_NAME_TRANSLATION_KEYS: Dict[str, Dict[str, str]] = {
    "hr-1": {
        "name": "agent.hr.assistant",  # 注意：實際上前端是 category + assistant，這裡簡化為直接使用 assistant
        "description": "agent.hr.description.assistant",
    },
    "hr-2": {
        "name": "agent.hr.trainingManager",
        "description": "agent.hr.description.trainingManager",
    },
    "hr-3": {
        "name": "agent.hr.performanceAnalysis",
        "description": "agent.hr.description.performanceAnalysis",
    },
    "hr-4": {
        "name": "agent.hr.employeeRelations",
        "description": "agent.hr.description.employeeRelations",
    },
    "hr-5": {
        "name": "agent.hr.compensationBenefits",
        "description": "agent.hr.description.compensationBenefits",
    },
    "hr-6": {
        "name": "agent.hr.talentDevelopment",
        "description": "agent.hr.description.talentDevelopment",
    },
    "log-1": {
        "name": "agent.logistics.supplyChainOptimization",
        "description": "agent.logistics.description.supplyChainOptimization",
    },
    "log-2": {
        "name": "agent.logistics.inventoryManagement",
        "description": "agent.logistics.description.inventoryManagement",
    },
    "log-3": {
        "name": "agent.logistics.routePlanning",
        "description": "agent.logistics.description.routePlanning",
    },
    "log-4": {
        "name": "agent.logistics.dataAnalysis",
        "description": "agent.logistics.description.dataAnalysis",
    },
    "log-5": {
        "name": "agent.logistics.supplierManagement",
        "description": "agent.logistics.description.supplierManagement",
    },
    "fin-1": {
        "name": "agent.finance.financialAnalyst",
        "description": "agent.finance.description.financialAnalyst",
    },
    "fin-2": {
        "name": "agent.finance.budgetPlanning",
        "description": "agent.finance.description.budgetPlanning",
    },
    "fin-3": {
        "name": "agent.finance.costControl",
        "description": "agent.finance.description.costControl",
    },
    "fin-4": {
        "name": "agent.finance.financialReportGeneration",
        "description": "agent.finance.description.financialReportGeneration",
    },
    "fin-5": {
        "name": "agent.finance.taxPlanning",
        "description": "agent.finance.description.taxPlanning",
    },
    "fin-6": {
        "name": "agent.finance.investmentAnalysis",
        "description": "agent.finance.description.investmentAnalysis",
    },
    "mes-1": {
        "name": "agent.mes.productionMonitoring",
        "description": "agent.mes.description.productionMonitoring",
    },
    "mes-2": {
        "name": "agent.mes.qualityControl",
        "description": "agent.mes.description.qualityControl",
    },
    "mes-3": {
        "name": "agent.mes.efficiencyAnalysis",
        "description": "agent.mes.description.efficiencyAnalysis",
    },
    "mes-4": {
        "name": "agent.mes.equipmentMaintenance",
        "description": "agent.mes.description.equipmentMaintenance",
    },
    "mes-5": {
        "name": "agent.mes.productionScheduling",
        "description": "agent.mes.description.productionScheduling",
    },
    "mes-6": {
        "name": "agent.mes.materialManagement",
        "description": "agent.mes.description.materialManagement",
    },
    "mes-7": {
        "name": "agent.mes.processOptimization",
        "description": "agent.mes.description.processOptimization",
    },
}

# hr-1 的特殊處理：名稱需要加上分類名稱
HR_ASSISTANT_NAME_PREFIX = {
    "en": "Human Resource ",
    "zh_CN": "人力资源",
    "zh_TW": "人力資源",
}


def get_translation(key: str, lang: str = "en") -> str:
    """獲取翻譯文本"""
    if key in TRANSLATIONS:
        return TRANSLATIONS[key].get(lang, TRANSLATIONS[key]["en"])
    return key


def convert_to_category_config(category_data: Dict[str, Any]) -> CategoryConfig:
    """將分類數據轉換為 CategoryConfig"""
    category_id = category_data["id"]
    category_key = f"agent.category.{category_id.replace('-', '')}"

    # 處理 human-resource 的特殊情況
    if category_id == "human-resource":
        category_key = "agent.category.humanResource"

    name = MultilingualText(
        en=get_translation(category_key, "en"),
        zh_CN=get_translation(category_key, "zh_CN"),
        zh_TW=get_translation(category_key, "zh_TW"),
    )

    return CategoryConfig(
        id=category_id,
        display_order=category_data["display_order"],
        is_visible=True,
        name=name,
    )


def convert_to_agent_config(
    agent_data: Dict[str, Any], category_id: str, display_order: int
) -> AgentConfig:
    """將代理數據轉換為 AgentConfig"""
    agent_id = agent_data["id"]

    # 獲取翻譯鍵名
    translation_keys = AGENT_NAME_TRANSLATION_KEYS.get(agent_id, {})
    name_key = translation_keys.get("name", "")
    description_key = translation_keys.get("description", "")

    # 處理 hr-1 的特殊情況：名稱需要加上分類名稱前綴
    if agent_id == "hr-1":
        name = MultilingualText(
            en=HR_ASSISTANT_NAME_PREFIX["en"] + get_translation(name_key, "en"),
            zh_CN=HR_ASSISTANT_NAME_PREFIX["zh_CN"] + get_translation(name_key, "zh_CN"),
            zh_TW=HR_ASSISTANT_NAME_PREFIX["zh_TW"] + get_translation(name_key, "zh_TW"),
        )
    else:
        name = MultilingualText(
            en=get_translation(name_key, "en"),
            zh_CN=get_translation(name_key, "zh_CN"),
            zh_TW=get_translation(name_key, "zh_TW"),
        )

    description = MultilingualText(
        en=get_translation(description_key, "en"),
        zh_CN=get_translation(description_key, "zh_CN"),
        zh_TW=get_translation(description_key, "zh_TW"),
    )

    return AgentConfig(
        id=agent_id,
        category_id=category_id,
        display_order=display_order,
        is_visible=True,
        name=name,
        description=description,
        icon=agent_data["icon"],
        status=agent_data["status"],
        usage_count=agent_data.get("usage_count"),
    )


def migrate_agent_display_config() -> None:
    """執行數據遷移"""
    print("開始遷移 Agent Display Config 數據...")

    # 創建 Store Service
    store_service = AgentDisplayConfigStoreService()

    # 遷移分類配置
    print("\n遷移分類配置...")
    for category_data in CATEGORIES_DATA:
        category_id = category_data["id"]
        print(f"  處理分類: {category_id}")

        try:
            # 檢查是否已存在
            existing = store_service.get_category_config(category_id, tenant_id=None)
            if existing:
                print(f"    分類 {category_id} 已存在，跳過")
                continue

            # 轉換並創建
            category_config = convert_to_category_config(category_data)
            store_service.create_category(
                category_config=category_config,
                tenant_id=None,  # 系統級配置
                created_by="migration_script",
            )
            print(f"    ✓ 分類 {category_id} 創建成功")
        except Exception as e:
            print(f"    ✗ 分類 {category_id} 創建失敗: {e}")
            raise

    # 遷移代理配置
    print("\n遷移代理配置...")
    total_agents = 0
    for category_data in CATEGORIES_DATA:
        category_id = category_data["id"]
        agents = category_data["agents"]

        print(f"  處理分類 {category_id} 的代理...")
        for idx, agent_data in enumerate(agents, start=1):
            agent_id = agent_data["id"]
            total_agents += 1

            try:
                # 檢查是否已存在
                existing = store_service.get_agent_config(agent_id, tenant_id=None)
                if existing:
                    print(f"    代理 {agent_id} 已存在，跳過")
                    continue

                # 轉換並創建
                agent_config = convert_to_agent_config(
                    agent_data=agent_data,
                    category_id=category_id,
                    display_order=idx,
                )
                store_service.create_agent(
                    agent_config=agent_config,
                    tenant_id=None,  # 系統級配置
                    created_by="migration_script",
                )
                print(f"    ✓ 代理 {agent_id} 創建成功")
            except Exception as e:
                print(f"    ✗ 代理 {agent_id} 創建失敗: {e}")
                raise

    print(f"\n遷移完成！共創建 {len(CATEGORIES_DATA)} 個分類，{total_agents} 個代理")


def validate_migration() -> bool:
    """驗證遷移結果"""
    print("\n驗證遷移結果...")

    store_service = AgentDisplayConfigStoreService()

    # 驗證分類
    categories = store_service.get_categories(tenant_id=None, include_inactive=False)
    print(f"  分類數量: {len(categories)} (預期: {len(CATEGORIES_DATA)})")

    if len(categories) != len(CATEGORIES_DATA):
        print("  ✗ 分類數量不匹配！")
        return False

    # 驗證代理
    total_agents = 0
    for category_data in CATEGORIES_DATA:
        category_id = category_data["id"]
        agents = store_service.get_agents_by_category(
            category_id=category_id, tenant_id=None, include_inactive=False
        )
        expected_count = len(category_data["agents"])
        actual_count = len(agents)
        total_agents += actual_count
        print(f"  分類 {category_id}: {actual_count} 個代理 (預期: {expected_count})")

        if actual_count != expected_count:
            print(f"    ✗ 分類 {category_id} 的代理數量不匹配！")
            return False

    expected_total = sum(len(cat["agents"]) for cat in CATEGORIES_DATA)
    print(f"  總代理數量: {total_agents} (預期: {expected_total})")

    if total_agents != expected_total:
        print("  ✗ 總代理數量不匹配！")
        return False

    print("  ✓ 驗證通過！")
    return True


if __name__ == "__main__":
    try:
        migrate_agent_display_config()
        if validate_migration():
            print("\n✅ 數據遷移成功完成！")
        else:
            print("\n⚠️ 數據遷移完成，但驗證失敗！")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ 數據遷移失敗: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
