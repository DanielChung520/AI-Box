# 代碼功能說明: 代理展示區示範數據種子腳本
# 創建日期: 2026-02-02
# 創建人: Daniel Chung
# 最後修改日期: 2026-02-02 00:00 UTC+8

"""代理展示區示範數據種子腳本

用於在新環境或遷移開發環境時，建立前端代理展示區的示範分類與代理卡片。
將 4 個分類（人力資源、物流、財務、生產管理）及 24 張代理卡片寫入 ArangoDB。

前置條件:
    - ArangoDB 已啟動且 .env 已配置
    - 請先啟用虛擬環境: source venv/bin/activate (或 uv run)

使用方式:
    python seed_agent_display_config.py [--force]
    --force: 若配置已存在則跳過（不覆蓋）
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# 確保專案根目錄在 sys.path
project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(dotenv_path=project_root / ".env")

import logging  # noqa: E402

from services.api.models.agent_display_config import (  # noqa: E402
    AgentConfig,
    CategoryConfig,
    MultilingualText,
)
from services.api.services.agent_display_config_store_service import (  # noqa: E402
    AgentDisplayConfigStoreService,
)

logger = logging.getLogger(__name__)


def _ml(en: str, zh_cn: str, zh_tw: str) -> MultilingualText:
    """建立多語言文本"""
    return MultilingualText(en=en, zh_CN=zh_cn, zh_TW=zh_tw)


def get_demo_categories() -> list[CategoryConfig]:
    """取得示範分類配置（4 個分類）"""
    return [
        CategoryConfig(
            id="human-resource",
            display_order=0,
            is_visible=True,
            name=_ml("Human Resources", "人力资源", "人力資源"),
            icon="fa-users",
            description=_ml(
                "Human resources management agents",
                "人力资源管理代理",
                "人力資源管理代理",
            ),
        ),
        CategoryConfig(
            id="logistics",
            display_order=1,
            is_visible=True,
            name=_ml("Logistics", "物流", "物流"),
            icon="fa-truck",
            description=_ml(
                "Logistics and supply chain agents",
                "物流与供应链代理",
                "物流與供應鏈代理",
            ),
        ),
        CategoryConfig(
            id="finance",
            display_order=2,
            is_visible=True,
            name=_ml("Finance", "财务", "財務"),
            icon="fa-coins",
            description=_ml(
                "Finance and accounting agents",
                "财务与会计代理",
                "財務與會計代理",
            ),
        ),
        CategoryConfig(
            id="mes",
            display_order=3,
            is_visible=True,
            name=_ml("Production Management", "生产管理", "生產管理"),
            icon="fa-industry",
            description=_ml(
                "Manufacturing execution system agents",
                "制造执行系统代理",
                "製造執行系統代理",
            ),
        ),
    ]


def get_demo_agents() -> list[AgentConfig]:
    """取得示範代理配置（24 張卡片）"""
    return [
        # 人力資源 (6)
        AgentConfig(
            id="hr-1",
            category_id="human-resource",
            display_order=0,
            is_visible=True,
            name=_ml("HR Assistant", "人力资源助理", "人力資源助理"),
            description=_ml(
                "General assistant for HR tasks",
                "适用于人力资源任务的通用助理",
                "適用於人力資源任務的通用助理",
            ),
            icon="fa-user-tie",
            status="online",
            usage_count=124,
        ),
        AgentConfig(
            id="hr-2",
            category_id="human-resource",
            display_order=1,
            is_visible=True,
            name=_ml("Recruitment Agent", "招聘代理", "招聘代理"),
            description=_ml(
                "Assists with recruitment and candidate screening",
                "协助招聘和候选人筛选",
                "協助招聘和候選人篩選",
            ),
            icon="fa-user-plus",
            status="online",
            usage_count=87,
        ),
        AgentConfig(
            id="hr-3",
            category_id="human-resource",
            display_order=2,
            is_visible=True,
            name=_ml("Training Agent", "培训代理", "培訓代理"),
            description=_ml(
                "Manages employee training and development",
                "管理员工培训与发展",
                "管理員工培訓與發展",
            ),
            icon="fa-graduation-cap",
            status="online",
            usage_count=65,
        ),
        AgentConfig(
            id="hr-4",
            category_id="human-resource",
            display_order=3,
            is_visible=True,
            name=_ml("Payroll Agent", "薪资代理", "薪資代理"),
            description=_ml(
                "Handles payroll and compensation queries",
                "处理薪资与薪酬查询",
                "處理薪資與薪酬查詢",
            ),
            icon="fa-money-bill-wave",
            status="online",
            usage_count=92,
        ),
        AgentConfig(
            id="hr-5",
            category_id="human-resource",
            display_order=4,
            is_visible=True,
            name=_ml("Performance Agent", "绩效代理", "績效代理"),
            description=_ml(
                "Supports performance review and evaluation",
                "支持绩效考核与评估",
                "支持績效考核與評估",
            ),
            icon="fa-chart-line",
            status="online",
            usage_count=58,
        ),
        AgentConfig(
            id="hr-6",
            category_id="human-resource",
            display_order=5,
            is_visible=True,
            name=_ml("Policy Agent", "政策代理", "政策代理"),
            description=_ml(
                "Answers HR policy and compliance questions",
                "回答人力资源政策与合规问题",
                "回答人力資源政策與合規問題",
            ),
            icon="fa-book",
            status="online",
            usage_count=43,
        ),
        # 物流 (5)
        AgentConfig(
            id="log-1",
            category_id="logistics",
            display_order=0,
            is_visible=True,
            name=_ml("Logistics Assistant", "物流助理", "物流助理"),
            description=_ml(
                "General assistant for logistics operations",
                "适用于物流运营的通用助理",
                "適用於物流營運的通用助理",
            ),
            icon="fa-truck",
            status="online",
            usage_count=156,
        ),
        AgentConfig(
            id="log-2",
            category_id="logistics",
            display_order=1,
            is_visible=True,
            name=_ml("Inventory Agent", "库存代理", "庫存代理"),
            description=_ml(
                "Manages inventory and stock levels",
                "管理库存与库存水平",
                "管理庫存與庫存水平",
            ),
            icon="fa-boxes-stacked",
            status="online",
            usage_count=98,
        ),
        AgentConfig(
            id="log-3",
            category_id="logistics",
            display_order=2,
            is_visible=True,
            name=_ml("Shipping Agent", "运输代理", "運輸代理"),
            description=_ml(
                "Handles shipping and delivery coordination",
                "处理运输与配送协调",
                "處理運輸與配送協調",
            ),
            icon="fa-ship",
            status="online",
            usage_count=129,
        ),
        AgentConfig(
            id="log-4",
            category_id="logistics",
            display_order=3,
            is_visible=True,
            name=_ml("Warehouse Agent", "仓储代理", "倉儲代理"),
            description=_ml(
                "Optimizes warehouse operations",
                "优化仓储运营",
                "優化倉儲營運",
            ),
            icon="fa-warehouse",
            status="online",
            usage_count=76,
        ),
        AgentConfig(
            id="log-5",
            category_id="logistics",
            display_order=4,
            is_visible=True,
            name=_ml("Supply Chain Agent", "供应链代理", "供應鏈代理"),
            description=_ml(
                "Analyzes supply chain and procurement",
                "分析供应链与采购",
                "分析供應鏈與採購",
            ),
            icon="fa-link",
            status="online",
            usage_count=64,
        ),
        # 財務 (6)
        AgentConfig(
            id="fin-1",
            category_id="finance",
            display_order=0,
            is_visible=True,
            name=_ml("Finance Assistant", "财务助理", "財務助理"),
            description=_ml(
                "General assistant for finance tasks",
                "适用于财务任务的通用助理",
                "適用於財務任務的通用助理",
            ),
            icon="fa-coins",
            status="online",
            usage_count=203,
        ),
        AgentConfig(
            id="fin-2",
            category_id="finance",
            display_order=1,
            is_visible=True,
            name=_ml("Accounting Agent", "会计代理", "會計代理"),
            description=_ml(
                "Handles accounting and bookkeeping",
                "处理会计与簿记",
                "處理會計與簿記",
            ),
            icon="fa-calculator",
            status="online",
            usage_count=112,
        ),
        AgentConfig(
            id="fin-3",
            category_id="finance",
            display_order=2,
            is_visible=True,
            name=_ml("Budget Agent", "预算代理", "預算代理"),
            description=_ml(
                "Supports budget planning and tracking",
                "支持预算规划与跟踪",
                "支持預算規劃與跟蹤",
            ),
            icon="fa-chart-pie",
            status="online",
            usage_count=89,
        ),
        AgentConfig(
            id="fin-4",
            category_id="finance",
            display_order=3,
            is_visible=True,
            name=_ml("Invoice Agent", "发票代理", "發票代理"),
            description=_ml(
                "Manages invoices and billing",
                "管理发票与账单",
                "管理發票與帳單",
            ),
            icon="fa-file-invoice",
            status="online",
            usage_count=157,
        ),
        AgentConfig(
            id="fin-5",
            category_id="finance",
            display_order=4,
            is_visible=True,
            name=_ml("Audit Agent", "审计代理", "審計代理"),
            description=_ml(
                "Assists with audit and compliance",
                "协助审计与合规",
                "協助審計與合規",
            ),
            icon="fa-magnifying-glass-chart",
            status="online",
            usage_count=54,
        ),
        AgentConfig(
            id="fin-6",
            category_id="finance",
            display_order=5,
            is_visible=True,
            name=_ml("Tax Agent", "税务代理", "稅務代理"),
            description=_ml(
                "Handles tax-related queries",
                "处理税务相关查询",
                "處理稅務相關查詢",
            ),
            icon="fa-receipt",
            status="online",
            usage_count=78,
        ),
        # 生產管理 (7)
        AgentConfig(
            id="mes-1",
            category_id="mes",
            display_order=0,
            is_visible=True,
            name=_ml("MES Assistant", "生产助理", "生產助理"),
            description=_ml(
                "General assistant for production management",
                "适用于生产管理的通用助理",
                "適用於生產管理的通用助理",
            ),
            icon="fa-industry",
            status="online",
            usage_count=256,
        ),
        AgentConfig(
            id="mes-2",
            category_id="mes",
            display_order=1,
            is_visible=True,
            name=_ml("Production Planning Agent", "生产计划代理", "生產計劃代理"),
            description=_ml(
                "Plans and schedules production",
                "规划与排程生产",
                "規劃與排程生產",
            ),
            icon="fa-calendar-check",
            status="online",
            usage_count=143,
        ),
        AgentConfig(
            id="mes-3",
            category_id="mes",
            display_order=2,
            is_visible=True,
            name=_ml("Quality Agent", "质量代理", "品質代理"),
            description=_ml(
                "Monitors quality control and inspection",
                "监控质量控制与检验",
                "監控品質控制與檢驗",
            ),
            icon="fa-clipboard-check",
            status="online",
            usage_count=109,
        ),
        AgentConfig(
            id="mes-4",
            category_id="mes",
            display_order=3,
            is_visible=True,
            name=_ml("Maintenance Agent", "维护代理", "維護代理"),
            description=_ml(
                "Manages equipment maintenance",
                "管理设备维护",
                "管理設備維護",
            ),
            icon="fa-wrench",
            status="online",
            usage_count=87,
        ),
        AgentConfig(
            id="mes-5",
            category_id="mes",
            display_order=4,
            is_visible=True,
            name=_ml("OEE Agent", "OEE 代理", "OEE 代理"),
            description=_ml(
                "Tracks overall equipment effectiveness",
                "跟踪设备综合效率",
                "跟蹤設備綜合效率",
            ),
            icon="fa-gauge-high",
            status="online",
            usage_count=95,
        ),
        AgentConfig(
            id="mes-6",
            category_id="mes",
            display_order=5,
            is_visible=True,
            name=_ml("Traceability Agent", "追溯代理", "追溯代理"),
            description=_ml(
                "Handles product traceability",
                "处理产品追溯",
                "處理產品追溯",
            ),
            icon="fa-barcode",
            status="online",
            usage_count=72,
        ),
        AgentConfig(
            id="mes-7",
            category_id="mes",
            display_order=6,
            is_visible=True,
            name=_ml("SOP Agent", "SOP 代理", "SOP 代理"),
            description=_ml(
                "Manages standard operating procedures",
                "管理标准作业程序",
                "管理標準作業程序",
            ),
            icon="fa-list-check",
            status="online",
            usage_count=68,
        ),
    ]


def seed_agent_display_config(force: bool = False) -> bool:
    """
    建立代理展示區示範數據

    Args:
        force: 若已存在則跳過（目前不覆蓋，僅跳過已存在項目）

    Returns:
        是否成功
    """
    try:
        store = AgentDisplayConfigStoreService()
    except RuntimeError as e:
        logger.error(f"ArangoDB 連線失敗: {e}")
        return False

    tenant_id: str | None = None  # 系統級配置

    # 1. 建立分類
    categories = get_demo_categories()
    for cat in categories:
        existing = store.get_category_config(cat.id, tenant_id)
        if existing and not force:
            logger.info(f"分類已存在，跳過: {cat.id}")
            continue
        if existing and force:
            logger.info(f"分類已存在，--force 時跳過: {cat.id}")
            continue
        try:
            store.create_category(cat, tenant_id=tenant_id, created_by="seed_script")
            logger.info(f"已建立分類: {cat.id}")
        except Exception as e:
            logger.error(f"建立分類失敗 {cat.id}: {e}")
            return False

    # 2. 建立代理
    agents = get_demo_agents()
    for agent in agents:
        existing = store.get_agent_config(agent.id, tenant_id)
        if existing and not force:
            logger.info(f"代理已存在，跳過: {agent.id}")
            continue
        if existing and force:
            logger.info(f"代理已存在，--force 時跳過: {agent.id}")
            continue
        try:
            store.create_agent(agent, tenant_id=tenant_id, created_by="seed_script")
            logger.info(f"已建立代理: {agent.id}")
        except Exception as e:
            logger.error(f"建立代理失敗 {agent.id}: {e}")
            return False

    return True


def main() -> int:
    """主程式"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="建立代理展示區示範數據（4 分類、24 代理卡片）")
    parser.add_argument(
        "--force",
        action="store_true",
        help="若配置已存在則跳過（目前不覆蓋，僅跳過）",
    )
    args = parser.parse_args()

    logger.info("開始建立代理展示區示範數據...")
    success = seed_agent_display_config(force=args.force)
    if success:
        logger.info("代理展示區示範數據建立完成")
        return 0
    logger.error("代理展示區示範數據建立失敗")
    return 1


if __name__ == "__main__":
    sys.exit(main())
