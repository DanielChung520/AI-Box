import { useState, useEffect } from 'react';
import { toast } from 'sonner';

// 定义支持的语言类型
type Language = 'en' | 'zh_CN' | 'zh_TW';

// 语言显示名称映射
export const languageNames: Record<Language, string> = {
  en: 'English',
  zh_CN: '简体中文',
  zh_TW: '繁體中文'
};

// 语言图标映射
export const languageIcons: Record<Language, string> = {
  en: 'fa-globe',
  zh_CN: 'fa-language',
  zh_TW: 'fa-language'
};

// 定义翻译内容类型
interface Translations {
  [key: string]: Record<Language, string>;
}

// 翻译内容
export const translations: Translations = {
  // 应用标题和欢迎信息
  'app.title': {
    en: 'AI GenAI Chat Room',
    zh_CN: 'AI智能聊天助手',
    zh_TW: 'AI智能聊天助手'
  },
  'welcome.message': {
    en: 'Welcome to GenAI Chat Assistant! Please select an Agent from the left or browse available Agents from the categories below.',
    zh_CN: '欢迎使用GenAI聊天助手！请从左侧选择一个Agent，或从下方的分类中浏览可用的Agent。',
    zh_TW: '歡迎使用GenAI聊天助手！請從左側選擇一個Agent，或從下方的分類中瀏覽可用的Agent。'
  },

  // 聊天区域
  'chat.title': {
    en: 'AI Chat Assistant',
    zh_CN: 'AI聊天助手',
    zh_TW: 'AI聊天助手'
  },
  'chat.task': {
    en: 'Task: ',
    zh_CN: '任务: ',
    zh_TW: '任務: '
  },
  'chat.aiAssistant': {
    en: 'AI Assistant',
    zh_CN: 'AI 助手',
    zh_TW: 'AI 助手'
  },
  'chat.user': {
    en: 'User',
    zh_CN: '用户',
    zh_TW: '用戶'
  },
  'chat.manage': {
    en: 'Manage',
    zh_CN: '管理',
    zh_TW: '管理'
  },
  'chat.manageAssistants': {
    en: 'Manage Assistants',
    zh_CN: '管理助理',
    zh_TW: '管理助理'
  },
  'chat.manageAgents': {
    en: 'Manage Agents',
    zh_CN: '管理代理',
    zh_TW: '管理代理'
  },
  'chat.expandPanel': {
    en: 'Expand Panel',
    zh_CN: '展开面板',
    zh_TW: '展開面板'
  },
  'chat.collapsePanel': {
    en: 'Collapse Panel',
    zh_CN: '收起面板',
    zh_TW: '收起面板'
  },

   // 侧边栏
  'sidebar.favorites': {
    en: 'Favorites',
    zh_CN: '收藏夹',
    zh_TW: '收藏夾'
  },
  'sidebar.tasks': {
    en: 'Tasks',
    zh_CN: '任务',
    zh_TW: '任務'
  },
  'sidebar.assistants': {
    en: 'Assistants',
    zh_CN: '助理',
    zh_TW: '助理'
  },
  'sidebar.agents': {
    en: 'Agents',
    zh_CN: '代理',
    zh_TW: '代理'
  },
  'sidebar.addTask': {
    en: 'Add Task',
    zh_CN: '新增任务',
    zh_TW: '新增任務'
  },
  'sidebar.toggle.expand': {
    en: 'Expand sidebar',
    zh_CN: '展开侧边栏',
    zh_TW: '展開側邊欄'
  },
  'sidebar.toggle.collapse': {
    en: 'Collapse sidebar',
    zh_CN: '收起侧边栏',
    zh_TW: '收起側邊欄'
  },
  'sidebar.user': {
    en: 'User',
    zh_CN: '用户',
    zh_TW: '用戶'
  },

  // 任务状态
  'status.pending': {
    en: 'Pending',
    zh_CN: '待处理',
    zh_TW: '待處理'
  },
  'status.in-progress': {
    en: 'In Progress',
    zh_CN: '进行中',
    zh_TW: '進行中'
  },
  'status.completed': {
    en: 'Completed',
    zh_CN: '已完成',
    zh_TW: '已完成'
  },

  // Agent状态
  'agent.status.online': {
    en: 'Online',
    zh_CN: '在线',
    zh_TW: '在線'
  },
  'agent.status.offline': {
    en: 'Offline',
    zh_CN: '离线',
    zh_TW: '離線'
  },
  'agent.status.maintenance': {
    en: 'Maintenance',
    zh_CN: '维护中',
    zh_TW: '維護中'
  },
  'agent.usage': {
    en: 'Usage Count: ',
    zh_CN: '使用次数: ',
    zh_TW: '使用次數: '
  },
  'agent.chat': {
    en: 'Chat',
    zh_CN: '对话',
    zh_TW: '對話'
  },

  // 聊天输入
  'chatInput.placeholder': {
    en: 'Enter your question...',
    zh_CN: '输入您的问题...',
    zh_TW: '輸入您的問題...'
  },
  'chatInput.send': {
    en: 'Send',
    zh_CN: '发送',
    zh_TW: '發送'
  },
  'chatInput.selectAssistant': {
    en: 'Select Assistant',
    zh_CN: '选择助理',
    zh_TW: '選擇助理'
  },
  'chatInput.assistant': {
    en: 'Assistant',
    zh_CN: '助理',
    zh_TW: '助理'
  },

  // 结果面板
  'resultPanel.files': {
    en: 'Files',
    zh_CN: '文件',
    zh_TW: '文件'
  },
  'resultPanel.preview': {
    en: 'Preview',
    zh_CN: '预览',
    zh_TW: '預覽'
  },

  // 主题切换
  'theme.toggle.dark': {
    en: 'Switch to dark theme',
    zh_CN: '切换到深色主题',
    zh_TW: '切換到深色主題'
  },
  'theme.toggle.light': {
    en: 'Switch to light theme',
    zh_CN: '切换到浅色主题',
    zh_TW: '切換到淺色主題'
  },
  'theme.toast.dark': {
    en: 'Switched to dark theme',
    zh_CN: '已切换到深色主题',
    zh_TW: '已切換到深色主題'
  },
  'theme.toast.light': {
    en: 'Switched to light theme',
    zh_CN: '已切换到浅色主题',
    zh_TW: '已切換到淺色主題'
  },

  // 语言切换
  'language.select': {
    en: 'Select Language',
    zh_CN: '选择语言',
    zh_TW: '選擇語言'
  },
  'language.toast': {
    en: 'Switched to ',
    zh_CN: '已切换到',
    zh_TW: '已切換到'
  },
  // 侧边栏更多翻译
  'sidebar.favorite1': {
    en: 'Analytics Report',
    zh_CN: '分析报告',
    zh_TW: '分析報告'
  },
  'sidebar.favorite2': {
    en: 'Meeting Notes',
    zh_CN: '会议记录',
    zh_TW: '會議記錄'
  },
  'sidebar.favorite3': {
    en: 'Project Plan',
    zh_CN: '项目计划',
    zh_TW: '項目計劃'
  },
  'sidebar.assistant1': {
    en: 'General Assistant',
    zh_CN: '通用助理',
    zh_TW: '通用助理'
  },
  'sidebar.assistant2': {
    en: 'Content Creator',
    zh_CN: '内容创作',
    zh_TW: '內容創作'
  },
  'sidebar.assistant3': {
    en: 'Data Analyst',
    zh_CN: '数据分析',
    zh_TW: '數據分析'
  },
  'sidebar.agent1': {
    en: 'Human Resources',
    zh_CN: '人力资源',
    zh_TW: '人力資源'
  },
  'sidebar.agent2': {
    en: 'Finance',
    zh_CN: '财务',
    zh_TW: '財務'
  },
  'sidebar.agent3': {
    en: 'Logistics',
    zh_CN: '物流',
    zh_TW: '物流'
  },
  'sidebar.agent4': {
    en: 'MES',
    zh_CN: '生产管理',
    zh_TW: '生產管理'
  },
  'sidebar.input.placeholder': {
    en: 'Enter task title...',
    zh_CN: '输入任务标题...',
    zh_TW: '輸入任務標題...'
  },
  'sidebar.button.add': {
    en: 'Add',
    zh_CN: '添加',
    zh_TW: '添加'
  },
  'sidebar.button.cancel': {
    en: 'Cancel',
    zh_CN: '取消',
    zh_TW: '取消'
  },
  'sidebar.user.email': {
    en: 'genai@example.com',
    zh_CN: 'genai@example.com',
    zh_TW: 'genai@example.com'
  },
  'sidebar.browse': {
    en: 'Browse',
    zh_CN: '浏览',
    zh_TW: '瀏覽'
  },
  'sidebar.browseAssistants': {
    en: 'Browse All Assistants',
    zh_CN: '浏览所有助理',
    zh_TW: '瀏覽所有助理'
  },
  'sidebar.browseAgents': {
    en: 'Browse All Agents',
    zh_CN: '浏览所有代理',
    zh_TW: '瀏覽所有代理'
  },

  // 模态框翻译
  'modal.selectAssistant': {
    en: 'Select Assistant',
    zh_CN: '选择助理',
    zh_TW: '選擇助理'
  },
  'modal.selectAgent': {
    en: 'Select Agent',
    zh_CN: '选择代理',
    zh_TW: '選擇代理'
  },
  'modal.close': {
    en: 'Close',
    zh_CN: '关闭',
    zh_TW: '關閉'
  },
  'modal.createNewTask': {
    en: 'Create New Task',
    zh_CN: '创建新任务',
    zh_TW: '創建新任務'
  },
  'modal.applyToCurrentTask': {
    en: 'Apply to Current Task',
    zh_CN: '应用到当前任务',
    zh_TW: '應用到當前任務'
  },
  'modal.cancel': {
    en: 'Cancel',
    zh_CN: '取消',
    zh_TW: '取消'
  },
  // 文件树翻译
  'sidebar.fileTree.reports': {
    en: 'Reports',
    zh_CN: '报告',
    zh_TW: '報告'
  },
  'sidebar.fileTree.weeklyReports': {
    en: 'Weekly Reports',
    zh_CN: '周报',
    zh_TW: '週報'
  },
  'sidebar.fileTree.monthlyReports': {
    en: 'Monthly Reports',
    zh_CN: '月报',
    zh_TW: '月報'
  },
  'sidebar.fileTree.analytics': {
    en: 'Analytics',
    zh_CN: '分析数据',
    zh_TW: '分析數據'
  },
  'sidebar.fileTree.documents': {
    en: 'Documents',
    zh_CN: '文档',
    zh_TW: '文檔'
  },
  'sidebar.fileTree.weeklyReport': {
    en: 'Weekly Report ',
    zh_CN: '周报',
    zh_TW: '週報'
  },
  'sidebar.fileTree.meetingNotes': {
    en: 'Meeting Notes',
    zh_CN: '会议记录',
    zh_TW: '會議記錄'
  },
  'sidebar.fileTree.readme': {
    en: 'README.md',
    zh_CN: 'README.md',
    zh_TW: 'README.md'
  },
  // Markdown查看器
  'markdownViewer.download': {
    en: 'Download',
    zh_CN: '下载',
    zh_TW: '下載'
  },
  'markdownViewer.more': {
    en: 'More',
    zh_CN: '更多',
    zh_TW: '更多'
  },

  // 任务相关翻译
  'task.salesReportRequest': {
    en: "Can you help me generate a sales data analysis report? It needs to include sales trend charts for the past three months.",
    zh_CN: "你能帮我生成一份销售数据分析报告吗？需要包含近三个月的销售趋势图表。",
    zh_TW: "你能幫我生成一份銷售數據分析報告嗎？需要包含近三個月的銷售趨勢圖表。"
  },

  // 助理类型翻译
  'assistant.general': {
    en: "General Assistant",
    zh_CN: "通用助手",
    zh_TW: "通用助手"
  },

  'assistant.creative': {
    en: "Creative Writing",
    zh_CN: "创意写作",
    zh_TW: "創意寫作"
  },

  'assistant.analyst': {
    en: "Data Analysis",
    zh_CN: "数据分析",
    zh_TW: "數據分析"
  },

   // Agent分类翻译
  'agent.category.humanResource': {
    en: "Human Resource",
    zh_CN: "人力资源",
    zh_TW: "人力資源"
  },
  // 兼容小写形式的键名
  'agent.category.humanresource': {
    en: "Human Resource",
    zh_CN: "人力资源",
    zh_TW: "人力資源"
  },

  'agent.category.logistics': {
    en: "Logistics",
    zh_CN: "物流",
    zh_TW: "物流"
  },

  'agent.category.finance': {
    en: "Finance",
    zh_CN: "财务",
    zh_TW: "財務"
  },

  'agent.category.mes': {
    en: "MES",
    zh_CN: "生产管理",
    zh_TW: "生產管理"
  },

  // Agent 詳細名稱和描述翻譯
  // HR Agents
  'agent.hr.assistant': {
    en: "Assistant",
    zh_CN: "助理",
    zh_TW: "助理"
  },
  'agent.hr.trainingManager': {
    en: "Training Manager",
    zh_CN: "培训管理员",
    zh_TW: "培訓管理員"
  },
  'agent.hr.performanceAnalysis': {
    en: "Performance Analysis",
    zh_CN: "绩效分析",
    zh_TW: "績效分析"
  },
  'agent.hr.employeeRelations': {
    en: "Employee Relations",
    zh_CN: "员工关系",
    zh_TW: "員工關係"
  },
  'agent.hr.compensationBenefits': {
    en: "Compensation & Benefits",
    zh_CN: "薪酬福利",
    zh_TW: "薪酬福利"
  },
  'agent.hr.talentDevelopment': {
    en: "Talent Development",
    zh_CN: "人才发展",
    zh_TW: "人才發展"
  },
  'agent.hr.description.assistant': {
    en: "Intelligent resume screening, interview scheduling, recruitment report generation",
    zh_CN: "智能筛选简历、安排面试、生成招聘报告",
    zh_TW: "智能篩選簡歷、安排面試、生成招聘報告"
  },
  'agent.hr.description.trainingManager': {
    en: "Design training courses, track learning progress, evaluate effectiveness",
    zh_CN: "设计培训课程、跟踪学习进度、评估效果",
    zh_TW: "設計培訓課程、跟蹤學習進度、評估效果"
  },
  'agent.hr.description.performanceAnalysis': {
    en: "Automated performance evaluation, provide improvement suggestions, generate reports",
    zh_CN: "自动化绩效评估、提供改进建议、生成报告",
    zh_TW: "自動化績效評估、提供改進建議、生成報告"
  },
  'agent.hr.description.employeeRelations': {
    en: "Handle employee inquiries, resolve conflicts, enhance team cohesion",
    zh_CN: "处理员工咨询、解决冲突、提升团队凝聚力",
    zh_TW: "處理員工諮詢、解決衝突、提升團隊凝聚力"
  },
  'agent.hr.description.compensationBenefits': {
    en: "Analyze market compensation, design benefit plans, optimize incentive mechanisms",
    zh_CN: "分析市场薪酬、设计福利方案、优化激励机制",
    zh_TW: "分析市場薪酬、設計福利方案、優化激勵機制"
  },
  'agent.hr.description.talentDevelopment': {
    en: "Identify high-potential talent, develop growth plans, build talent pipeline",
    zh_CN: "识别高潜人才、制定发展计划、构建人才梯队",
    zh_TW: "識別高潛人才、制定發展計劃、構建人才梯隊"
  },

  // Logistics Agents
  'agent.logistics.supplyChainOptimization': {
    en: "Supply Chain Optimization",
    zh_CN: "供应链优化",
    zh_TW: "供應鏈優化"
  },
  'agent.logistics.inventoryManagement': {
    en: "Inventory Management",
    zh_CN: "库存管理",
    zh_TW: "庫存管理"
  },
  'agent.logistics.routePlanning': {
    en: "Transport Route Planning",
    zh_CN: "运输路线规划",
    zh_TW: "運輸路線規劃"
  },
  'agent.logistics.dataAnalysis': {
    en: "Logistics Data Analysis",
    zh_CN: "物流数据分析",
    zh_TW: "物流數據分析"
  },
  'agent.logistics.supplierManagement': {
    en: "Supplier Management",
    zh_CN: "供应商管理",
    zh_TW: "供應商管理"
  },
  'agent.logistics.description.supplyChainOptimization': {
    en: "Analyze supply chain data, provide optimization suggestions, predict demand",
    zh_CN: "分析供应链数据、提供优化建议、预测需求",
    zh_TW: "分析供應鏈數據、提供優化建議、預測需求"
  },
  'agent.logistics.description.inventoryManagement': {
    en: "Monitor inventory levels, predict demand, generate replenishment suggestions",
    zh_CN: "监控库存水平、预测需求、生成补货建议",
    zh_TW: "監控庫存水平、預測需求、生成補貨建議"
  },
  'agent.logistics.description.routePlanning': {
    en: "Optimize delivery routes, reduce transportation costs, improve delivery efficiency",
    zh_CN: "优化配送路线、降低运输成本、提高配送效率",
    zh_TW: "優化配送路線、降低運輸成本、提高配送效率"
  },
  'agent.logistics.description.dataAnalysis': {
    en: "Analyze logistics performance, identify improvement points, generate data reports",
    zh_CN: "分析物流绩效、识别改进点、生成数据报告",
    zh_TW: "分析物流績效、識別改進點、生成數據報告"
  },
  'agent.logistics.description.supplierManagement': {
    en: "Evaluate supplier performance, manage partnerships, optimize procurement processes",
    zh_CN: "评估供应商绩效、管理合作关系、优化采购流程",
    zh_TW: "評估供應商績效、管理合作關係、優化採購流程"
  },

  // Finance Agents
  'agent.finance.financialAnalyst': {
    en: "Financial Analyst",
    zh_CN: "财务分析师",
    zh_TW: "財務分析師"
  },
  'agent.finance.budgetPlanning': {
    en: "Budget Planning",
    zh_CN: "预算规划",
    zh_TW: "預算規劃"
  },
  'agent.finance.costControl': {
    en: "Cost Control",
    zh_CN: "成本控制",
    zh_TW: "成本控制"
  },
  'agent.finance.financialReportGeneration': {
    en: "Financial Report Generation",
    zh_CN: "财务报表生成",
    zh_TW: "財務報表生成"
  },
  'agent.finance.taxPlanning': {
    en: "Tax Planning",
    zh_CN: "税务筹划",
    zh_TW: "稅務籌劃"
  },
  'agent.finance.investmentAnalysis': {
    en: "Investment Analysis",
    zh_CN: "投资分析",
    zh_TW: "投資分析"
  },
  'agent.finance.description.financialAnalyst': {
    en: "Analyze financial data, generate reports, provide decision support",
    zh_CN: "分析财务数据、生成报表、提供决策支持",
    zh_TW: "分析財務數據、生成報表、提供決策支持"
  },
  'agent.finance.description.budgetPlanning': {
    en: "Assist in budget development, track expenses, forecast financial status",
    zh_CN: "协助制定预算、跟踪支出、预测财务状况",
    zh_TW: "協助制定預算、跟蹤支出、預測財務狀況"
  },
  'agent.finance.description.costControl': {
    en: "Analyze cost structure, identify savings opportunities, optimize cost management",
    zh_CN: "分析成本结构、识别节约机会、优化成本管理",
    zh_TW: "分析成本結構、識別節約機會、優化成本管理"
  },
  'agent.finance.description.financialReportGeneration': {
    en: "Automatically generate various financial reports, ensure data accuracy",
    zh_CN: "自动化生成各类财务报表、确保数据准确性",
    zh_TW: "自動化生成各類財務報表、確保數據準確性"
  },
  'agent.finance.description.taxPlanning': {
    en: "Analyze tax policies, provide compliance advice, optimize tax structure",
    zh_CN: "分析税务政策、提供合规建议、优化税务结构",
    zh_TW: "分析稅務政策、提供合規建議、優化稅務結構"
  },
  'agent.finance.description.investmentAnalysis': {
    en: "Evaluate investment projects, predict returns, provide investment advice",
    zh_CN: "评估投资项目、预测回报、提供投资建议",
    zh_TW: "評估投資項目、預測回報、提供投資建議"
  },

  // MES Agents
  'agent.mes.productionMonitoring': {
    en: "Production Monitoring",
    zh_CN: "生产监控",
    zh_TW: "生產監控"
  },
  'agent.mes.qualityControl': {
    en: "Quality Control",
    zh_CN: "质量控制",
    zh_TW: "質量控制"
  },
  'agent.mes.efficiencyAnalysis': {
    en: "Efficiency Analysis",
    zh_CN: "效率分析",
    zh_TW: "效率分析"
  },
  'agent.mes.equipmentMaintenance': {
    en: "Equipment Maintenance",
    zh_CN: "设备维护",
    zh_TW: "設備維護"
  },
  'agent.mes.productionScheduling': {
    en: "Production Scheduling",
    zh_CN: "生产排程",
    zh_TW: "生產排程"
  },
  'agent.mes.materialManagement': {
    en: "Material Management",
    zh_CN: "物料管理",
    zh_TW: "物料管理"
  },
  'agent.mes.processOptimization': {
    en: "Process Parameter Optimization",
    zh_CN: "工艺参数优化",
    zh_TW: "工藝參數優化"
  },
  'agent.mes.description.productionMonitoring': {
    en: "Real-time monitoring of production processes, detect anomalies, provide alerts",
    zh_CN: "实时监控生产流程、检测异常、提供预警",
    zh_TW: "實時監控生產流程、檢測異常、提供預警"
  },
  'agent.mes.description.qualityControl': {
    en: "Analyze quality data, identify issues, provide improvement suggestions",
    zh_CN: "分析质量数据、识别问题、提供改进建议",
    zh_TW: "分析質量數據、識別問題、提供改進建議"
  },
  'agent.mes.description.efficiencyAnalysis': {
    en: "Evaluate production efficiency, identify bottlenecks, provide optimization solutions",
    zh_CN: "评估生产效率、识别瓶颈、提供优化方案",
    zh_TW: "評估生產效率、識別瓶頸、提供優化方案"
  },
  'agent.mes.description.equipmentMaintenance': {
    en: "Predict equipment failures, develop maintenance plans, optimize equipment utilization",
    zh_CN: "预测设备故障、制定维护计划、优化设备利用率",
    zh_TW: "預測設備故障、制定維護計劃、優化設備利用率"
  },
  'agent.mes.description.productionScheduling': {
    en: "Optimize production plans, arrange resources reasonably, improve on-time delivery rate",
    zh_CN: "优化生产计划、合理安排资源、提高交付准时率",
    zh_TW: "優化生產計劃、合理安排資源、提高交付準時率"
  },
  'agent.mes.description.materialManagement': {
    en: "Track material usage, optimize material distribution, reduce inventory backlog",
    zh_CN: "跟踪物料使用、优化物料配送、减少库存积压",
    zh_TW: "跟蹤物料使用、優化物料配送、減少庫存積壓"
  },
  'agent.mes.description.processOptimization': {
    en: "Analyze process data, optimize parameter settings, improve product quality",
    zh_CN: "分析工艺数据、优化参数设置、提高产品质量",
    zh_TW: "分析工藝數據、優化參數設置、提高產品質量"
  },

  // 文件樹相關翻譯
  'fileTree.analyticsReport': {
    en: "Data Analysis Report",
    zh_CN: "数据分析报告",
    zh_TW: "數據分析報告"
  },
  'fileTree.salesForecast': {
    en: "Sales Forecast",
    zh_CN: "销售预测",
    zh_TW: "銷售預測"
  },
  'fileTree.meetingRecord': {
    en: "Meeting Record",
    zh_CN: "会议记录",
    zh_TW: "會議記錄"
  },
  'fileTree.meetingRecordWithDate': {
    en: "Meeting Record",
    zh_CN: "会议记录",
    zh_TW: "會議記錄"
  },

  // 通用翻譯
  'common.comingSoon': {
    en: "Coming soon",
    zh_CN: "即将推出",
    zh_TW: "即將推出"
  },
  'common.empty': {
    en: "Empty",
    zh_CN: "空",
    zh_TW: "空"
  },
  'common.otherPage': {
    en: "Other Page - Coming Soon",
    zh_CN: "其他頁面 - 即將推出",
    zh_TW: "其他頁面 - 即將推出"
  },

  // Agent 註冊相關翻譯
  'agentRegistration.title': {
    en: 'Register New Agent Service',
    zh_CN: '註冊新代理服務',
    zh_TW: '註冊新 Agent 服務'
  },
  'agentRegistration.tabs.basic': {
    en: 'Basic Information',
    zh_CN: '基本資訊',
    zh_TW: '基本資訊'
  },
  'agentRegistration.tabs.endpoints': {
    en: 'Endpoint Configuration',
    zh_CN: '端點配置',
    zh_TW: '端點配置'
  },
  'agentRegistration.tabs.permissions': {
    en: 'Permissions',
    zh_CN: '權限配置',
    zh_TW: '權限配置'
  },
  'agentRegistration.internalOnly': {
    en: 'Internal Only',
    zh_CN: '僅內部代理',
    zh_TW: '僅內部 Agent'
  },
  'agentRegistration.fields.agentId': {
    en: 'Agent ID',
    zh_CN: '代理 ID',
    zh_TW: 'Agent ID'
  },
  'agentRegistration.fields.agentName': {
    en: 'Agent Name',
    zh_CN: '代理名稱',
    zh_TW: 'Agent 名稱'
  },
  'agentRegistration.fields.agentType': {
    en: 'Agent Type',
    zh_CN: '代理類型',
    zh_TW: 'Agent 類型'
  },
  'agentRegistration.fields.description': {
    en: 'Description',
    zh_CN: '描述',
    zh_TW: '描述'
  },
  'agentRegistration.fields.capabilities': {
    en: 'Capabilities',
    zh_CN: '能力列表',
    zh_TW: '能力列表'
  },
  'agentRegistration.fields.isInternal': {
    en: 'Internal Agent (running in the same system)',
    zh_CN: '內部代理（運行在同一系統中）',
    zh_TW: '內部 Agent（運行在同一系統中）'
  },
  'agentRegistration.fields.protocol': {
    en: 'Protocol Type',
    zh_CN: '協議類型',
    zh_TW: '協議類型'
  },
  'agentRegistration.fields.httpEndpoint': {
    en: 'HTTP Endpoint URL',
    zh_CN: 'HTTP 端點 URL',
    zh_TW: 'HTTP 端點 URL'
  },
  'agentRegistration.fields.mcpEndpoint': {
    en: 'MCP Endpoint URL',
    zh_CN: 'MCP 端點 URL',
    zh_TW: 'MCP 端點 URL'
  },
  'agentRegistration.fields.authType': {
    en: 'Authentication Method',
    zh_CN: '認證方式',
    zh_TW: '認證方式'
  },
  'agentRegistration.fields.apiKey': {
    en: 'API Key',
    zh_CN: 'API 密鑰',
    zh_TW: 'API Key'
  },
  'agentRegistration.fields.serverCertificate': {
    en: 'Server Certificate',
    zh_CN: '服務器證書',
    zh_TW: '服務器證書'
  },
  'agentRegistration.fields.ipWhitelist': {
    en: 'IP Whitelist',
    zh_CN: 'IP 白名單',
    zh_TW: 'IP 白名單'
  },
  'agentRegistration.fields.allowedMemoryNamespaces': {
    en: 'Allowed Memory Namespaces',
    zh_CN: '允許訪問的 Memory 命名空間',
    zh_TW: '允許訪問的 Memory 命名空間'
  },
  'agentRegistration.fields.allowedTools': {
    en: 'Allowed Tools',
    zh_CN: '允許使用的工具',
    zh_TW: '允許使用的工具'
  },
  'agentRegistration.fields.allowedLlmProviders': {
    en: 'Allowed LLM Providers',
    zh_CN: '允許使用的 LLM Provider',
    zh_TW: '允許使用的 LLM Provider'
  },
  'agentRegistration.placeholders.agentId': {
    en: 'e.g., my-agent-001',
    zh_CN: '例如：my-agent-001',
    zh_TW: '例如：my-agent-001'
  },
  'agentRegistration.placeholders.agentName': {
    en: 'e.g., My Custom Agent',
    zh_CN: '例如：我的自定義代理',
    zh_TW: '例如：My Custom Agent'
  },
  'agentRegistration.placeholders.description': {
    en: 'Describe the functionality and purpose of this Agent',
    zh_CN: '描述此代理的功能和用途',
    zh_TW: '描述此 Agent 的功能和用途'
  },
  'agentRegistration.placeholders.capability': {
    en: 'Enter capability and press Enter to add',
    zh_CN: '輸入能力並按 Enter 添加',
    zh_TW: '輸入能力並按 Enter 添加'
  },
  'agentRegistration.placeholders.httpEndpoint': {
    en: 'https://example.com/api/agent',
    zh_CN: 'https://example.com/api/agent',
    zh_TW: 'https://example.com/api/agent'
  },
  'agentRegistration.placeholders.mcpEndpoint': {
    en: 'mcp://example.com:8080',
    zh_CN: 'mcp://example.com:8080',
    zh_TW: 'mcp://example.com:8080'
  },
  'agentRegistration.placeholders.apiKey': {
    en: 'Enter API Key',
    zh_CN: '輸入 API 密鑰',
    zh_TW: '輸入 API Key'
  },
  'agentRegistration.placeholders.certificate': {
    en: 'Paste certificate here...',
    zh_CN: '粘貼證書內容...',
    zh_TW: '貼上證書內容...'
  },
  'agentRegistration.placeholders.ip': {
    en: 'e.g., 192.168.1.0/24',
    zh_CN: '例如：192.168.1.0/24',
    zh_TW: '例如：192.168.1.0/24'
  },
  'agentRegistration.placeholders.memoryNamespaces': {
    en: 'Comma-separated, e.g., ns1,ns2',
    zh_CN: '用逗號分隔，例如：ns1,ns2',
    zh_TW: '用逗號分隔，例如：ns1,ns2'
  },
  'agentRegistration.placeholders.tools': {
    en: 'Comma-separated, e.g., tool1,tool2',
    zh_CN: '用逗號分隔，例如：tool1,tool2',
    zh_TW: '用逗號分隔，例如：tool1,tool2'
  },
  'agentRegistration.placeholders.llmProviders': {
    en: 'Comma-separated, e.g., openai,anthropic',
    zh_CN: '用逗號分隔，例如：openai,anthropic',
    zh_TW: '用逗號分隔，例如：openai,anthropic'
  },
  'agentRegistration.selectAgentType': {
    en: 'Select Agent Type',
    zh_CN: '選擇代理類型',
    zh_TW: '選擇 Agent 類型'
  },
  'agentRegistration.types.planning': {
    en: 'Planning (Planning)',
    zh_CN: '規劃（Planning）',
    zh_TW: 'Planning (規劃)'
  },
  'agentRegistration.types.execution': {
    en: 'Execution (Execution)',
    zh_CN: '執行（Execution）',
    zh_TW: 'Execution (執行)'
  },
  'agentRegistration.types.review': {
    en: 'Review (Review)',
    zh_CN: '審查（Review）',
    zh_TW: 'Review (審查)'
  },
  'agentRegistration.auth.none': {
    en: 'None (Use configuration below)',
    zh_CN: '無（使用下方配置）',
    zh_TW: '無（使用下方配置）'
  },
  'agentRegistration.auth.apiKey': {
    en: 'API Key',
    zh_CN: 'API 密鑰',
    zh_TW: 'API Key'
  },
  'agentRegistration.auth.mtls': {
    en: 'mTLS Certificate',
    zh_CN: 'mTLS 證書',
    zh_TW: 'mTLS 證書'
  },
  'agentRegistration.auth.ipWhitelist': {
    en: 'IP Whitelist',
    zh_CN: 'IP 白名單',
    zh_TW: 'IP 白名單'
  },
  'agentRegistration.hints.isInternal': {
    en: 'Internal agents do not require endpoint configuration and will directly call local services',
    zh_CN: '內部代理不需要端點配置，會直接調用本地服務',
    zh_TW: '內部 Agent 不需要端點配置，會直接調用本地服務'
  },
  'agentRegistration.sections.resourceAccess': {
    en: 'Resource Access Permissions (Optional)',
    zh_CN: '資源訪問權限（可選）',
    zh_TW: '資源訪問權限（可選）'
  },
  'agentRegistration.submit': {
    en: 'Register Agent',
    zh_CN: '註冊代理',
    zh_TW: '註冊 Agent'
  },
  'agentRegistration.submitting': {
    en: 'Registering...',
    zh_CN: '註冊中...',
    zh_TW: '註冊中...'
  },
  'agentRegistration.errors.agentIdRequired': {
    en: 'Agent ID is required',
    zh_CN: '代理 ID 為必填項',
    zh_TW: 'Agent ID 為必填項'
  },
  'agentRegistration.errors.agentNameRequired': {
    en: 'Agent name is required',
    zh_CN: '代理名稱為必填項',
    zh_TW: 'Agent 名稱為必填項'
  },
  'agentRegistration.errors.agentTypeRequired': {
    en: 'Agent type is required',
    zh_CN: '代理類型為必填項',
    zh_TW: 'Agent 類型為必填項'
  },
  'agentRegistration.errors.httpEndpointRequired': {
    en: 'HTTP endpoint is required',
    zh_CN: 'HTTP 端點為必填項',
    zh_TW: 'HTTP 端點為必填項'
  },
  'agentRegistration.errors.mcpEndpointRequired': {
    en: 'MCP endpoint is required',
    zh_CN: 'MCP 端點為必填項',
    zh_TW: 'MCP 端點為必填項'
  },
  'agentRegistration.errors.authRequired': {
    en: 'External agents must provide at least one authentication method',
    zh_CN: '外部代理必須提供至少一種認證方式',
    zh_TW: '外部 Agent 必須提供至少一種認證方式'
  },
  'agentRegistration.errors.apiKeyRequired': {
    en: 'API Key is required',
    zh_CN: 'API 密鑰為必填項',
    zh_TW: 'API Key 為必填項'
  },
  'agentRegistration.errors.certificateRequired': {
    en: 'Server certificate is required',
    zh_CN: '服務器證書為必填項',
    zh_TW: '服務器證書為必填項'
  },
  'agentRegistration.errors.submitFailed': {
    en: 'Registration failed, please try again later',
    zh_CN: '註冊失敗，請稍後再試',
    zh_TW: '註冊失敗，請稍後再試'
  },
  'agentRegistration.fields.secretAuth': {
    en: 'External Agent Authentication',
    zh_CN: '外部代理身份驗證',
    zh_TW: '外部 Agent 身份驗證'
  },
  'agentRegistration.fields.secretId': {
    en: 'Secret ID (issued by AI-Box)',
    zh_CN: 'Secret ID（由 AI-Box 簽發）',
    zh_TW: 'Secret ID（由 AI-Box 簽發）'
  },
  'agentRegistration.fields.secretKey': {
    en: 'Secret Key (issued by AI-Box)',
    zh_CN: 'Secret Key（由 AI-Box 簽發）',
    zh_TW: 'Secret Key（由 AI-Box 簽發）'
  },
  'agentRegistration.hints.secretAuth': {
    en: 'Please use the Secret ID and Secret Key issued by AI-Box for authentication',
    zh_CN: '請使用由 AI-Box 簽發的 Secret ID 和 Secret Key 進行身份驗證',
    zh_TW: '請使用由 AI-Box 簽發的 Secret ID 和 Secret Key 進行身份驗證'
  },
  'agentRegistration.placeholders.secretId': {
    en: 'e.g., aibox-example-1234567890-abc123',
    zh_CN: '例如：aibox-example-1234567890-abc123',
    zh_TW: '例如：aibox-example-1234567890-abc123'
  },
  'agentRegistration.placeholders.secretKey': {
    en: 'Enter Secret Key',
    zh_CN: '輸入 Secret Key',
    zh_TW: '輸入 Secret Key'
  },
  'agentRegistration.secretVerified': {
    en: 'Secret verified successfully',
    zh_CN: 'Secret 驗證成功',
    zh_TW: 'Secret 驗證成功'
  },
  'agentRegistration.verifySecret': {
    en: 'Verify Secret',
    zh_CN: '驗證 Secret',
    zh_TW: '驗證 Secret'
  },
  'agentRegistration.verifyingSecret': {
    en: 'Verifying...',
    zh_CN: '驗證中...',
    zh_TW: '驗證中...'
  },
  'agentRegistration.noSecret': {
    en: 'No Secret ID?',
    zh_CN: '還沒有 Secret ID？',
    zh_TW: '還沒有 Secret ID？'
  },
  'agentRegistration.applySecret': {
    en: 'Click here to apply',
    zh_CN: '點擊這裡申請',
    zh_TW: '點擊這裡申請'
  },
  'agentRegistration.applySecretHint': {
    en: 'Secret application feature will be implemented in Phase 2',
    zh_CN: 'Secret 申請功能將在 Phase 2 實現',
    zh_TW: 'Secret 申請功能將在 Phase 2 實現'
  },
  'agentRegistration.errors.secretRequired': {
    en: 'Please enter Secret ID and Secret Key',
    zh_CN: '請輸入 Secret ID 和 Secret Key',
    zh_TW: '請輸入 Secret ID 和 Secret Key'
  },
  'agentRegistration.errors.secretInvalid': {
    en: 'Invalid Secret ID or Secret Key',
    zh_CN: 'Secret ID 或 Secret Key 無效',
    zh_TW: 'Secret ID 或 Secret Key 無效'
  },
  'agentRegistration.errors.secretAlreadyBound': {
    en: 'This Secret ID is already bound to another agent',
    zh_CN: '此 Secret ID 已被綁定到其他代理',
    zh_TW: '此 Secret ID 已被綁定到其他 Agent'
  },
  'agentRegistration.errors.secretVerificationFailed': {
    en: 'Secret verification failed, please try again later',
    zh_CN: 'Secret 驗證失敗，請稍後再試',
    zh_TW: 'Secret 驗證失敗，請稍後再試'
  },
  'agentRegistration.errors.secretNotVerified': {
    en: 'Please verify Secret ID and Secret Key first',
    zh_CN: '請先驗證 Secret ID 和 Secret Key',
    zh_TW: '請先驗證 Secret ID 和 Secret Key'
  },

  // 消息操作按鈕翻譯
  'messageActions.like': {
    en: 'Like',
    zh_CN: '点赞',
    zh_TW: '點讚'
  },
  'messageActions.dislike': {
    en: 'Dislike',
    zh_CN: '倒赞',
    zh_TW: '倒讚'
  },
  'messageActions.copy': {
    en: 'Copy',
    zh_CN: '复制',
    zh_TW: '複製'
  },
  'messageActions.copied': {
    en: 'Copied',
    zh_CN: '已复制',
    zh_TW: '已複製'
  },

  // Mermaid 圖表翻譯
  'mermaid.showCode': {
    en: 'Show Code',
    zh_CN: '显示代码',
    zh_TW: '顯示代碼'
  },
  'mermaid.showChart': {
    en: 'Show Chart',
    zh_CN: '显示图表',
    zh_TW: '顯示圖表'
  },

  // 代碼塊翻譯
  'codeBlock.copy': {
    en: 'Copy',
    zh_CN: '复制',
    zh_TW: '複製'
  },
  'codeBlock.copied': {
    en: 'Copied',
    zh_CN: '已复制',
    zh_TW: '已複製'
  },

  // 助理相關翻譯
  'assistant.favorite.add': {
    en: 'Add to Favorites',
    zh_CN: '加入收藏',
    zh_TW: '加入收藏'
  },
  'assistant.favorite.remove': {
    en: 'Remove from Favorites',
    zh_CN: '取消收藏',
    zh_TW: '取消收藏'
  },
  'assistant.actions.maintain': {
    en: 'Maintain',
    zh_CN: '维护',
    zh_TW: '維護'
  },
  'assistant.actions.edit': {
    en: 'Edit',
    zh_CN: '编辑',
    zh_TW: '編輯'
  },
  'assistant.actions.delete': {
    en: 'Delete',
    zh_CN: '删除',
    zh_TW: '刪除'
  },
  'assistant.delete.title': {
    en: 'Delete Assistant',
    zh_CN: '删除助理',
    zh_TW: '刪除助理'
  },
  'assistant.delete.confirm': {
    en: 'Are you sure you want to delete this assistant? This action cannot be undone.',
    zh_CN: '确定要删除此助理吗？此操作无法撤销。',
    zh_TW: '確定要刪除此助理嗎？此操作無法撤銷。'
  },
  'assistant.delete.confirmButton': {
    en: 'Delete',
    zh_CN: '删除',
    zh_TW: '刪除'
  },
  'assistant.delete.cancelButton': {
    en: 'Cancel',
    zh_CN: '取消',
    zh_TW: '取消'
  },

  // 聊天输入相关翻译
  'chatInput.agent': {
    en: 'Agent',
    zh_CN: '代理',
    zh_TW: '代理'
  },
  'chatInput.selectAgent': {
    en: 'Select Agent',
    zh_CN: '选择代理',
    zh_TW: '選擇代理'
  },
  'chatInput.model.auto': {
    en: 'Auto',
    zh_CN: '自动',
    zh_TW: '自動'
  },
  'chatInput.selectModel': {
    en: 'Select Model',
    zh_CN: '选择模型',
    zh_TW: '選擇模型'
  },
  'chat.noMessages': {
    en: 'No messages yet, start a conversation!',
    zh_CN: '还没有消息，开始对话吧！',
    zh_TW: '還沒有消息，開始對話吧！'
  },

  // 提及功能翻译
  'chatInput.mention.title': {
    en: 'Mention',
    zh_CN: '提及',
    zh_TW: '提及'
  },
  'chatInput.mention.file': {
    en: 'File',
    zh_CN: '文件',
    zh_TW: '文件'
  },
  'chatInput.mention.fileDesc': {
    en: 'Mention a file',
    zh_CN: '提及文件',
    zh_TW: '提及文件'
  },
  'chatInput.mention.code': {
    en: 'Code',
    zh_CN: '代码',
    zh_TW: '代碼'
  },
  'chatInput.mention.codeDesc': {
    en: 'Mention a code snippet',
    zh_CN: '提及代码片段',
    zh_TW: '提及代碼片段'
  },
  'chatInput.mention.context': {
    en: 'Context',
    zh_CN: '上下文',
    zh_TW: '上下文'
  },
  'chatInput.mention.contextDesc': {
    en: 'Mention context',
    zh_CN: '提及上下文',
    zh_TW: '提及上下文'
  },
  'chatInput.mention.variable': {
    en: 'Variable',
    zh_CN: '变量',
    zh_TW: '變量'
  },
  'chatInput.mention.variableDesc': {
    en: 'Mention a variable',
    zh_CN: '提及变量',
    zh_TW: '提及變量'
  },
  'chatInput.mention.function': {
    en: 'Function',
    zh_CN: '函数',
    zh_TW: '函數'
  },
  'chatInput.mention.functionDesc': {
    en: 'Mention a function',
    zh_CN: '提及函数',
    zh_TW: '提及函數'
  }
}

export function useLanguage() {
  // 默认语言为繁体中文
  const [language, setLanguage] = useState<Language>('zh_TW');
  // 添加更新计数器以确保强制重新渲染
  const [updateCounter, setUpdateCounter] = useState(0);

  // 初始化时从localStorage获取或设置默认值
  useEffect(() => {
    const savedLanguage = localStorage.getItem('language') as Language;
    if (savedLanguage && Object.keys(languageNames).includes(savedLanguage)) {
      setLanguage(savedLanguage);
    } else {
      // 如果没有保存的语言或保存的语言无效，设置为默认的繁体中文
      localStorage.setItem('language', 'zh_TW');
      setLanguage('zh_TW');
    }
  }, []);

  // 保存语言设置到localStorage并更新文档lang属性
  useEffect(() => {
    localStorage.setItem('language', language);
    // 將語言代碼轉換為 HTML lang 屬性格式（zh_TW -> zh-TW）
    const htmlLang = language === 'zh_TW' ? 'zh-TW' : language === 'zh_CN' ? 'zh-CN' : language;
    document.documentElement.lang = htmlLang;
    // 增加计数器以强制更新所有使用此hook的组件
    setUpdateCounter(prev => prev + 1);
  }, [language]);

  // 翻译函数 - 移除useCallback以确保每次语言变更时都返回新的函数引用
  const t = (key: string, fallback?: string): string => {
    if (translations[key] && translations[key][language]) {
      return translations[key][language];
    }
    return fallback || key;
  };

  // 直接设置语言的函数
  const setLanguageDirect = (newLanguage: Language) => {
    if (Object.keys(languageNames).includes(newLanguage)) {
      // 注意：setLanguage 会触发 useEffect，在 useEffect 中会更新 updateCounter
      // 所以这里不需要手动更新 updateCounter
      setLanguage(newLanguage);
    }
  };

  // 切换语言函数（带toast提示）
  const toggleLanguage = (newLanguage: Language) => {
    if (Object.keys(languageNames).includes(newLanguage)) {
      setLanguage(newLanguage);

      // 强制触发重新渲染
      setUpdateCounter(prev => prev + 1);

      // 显示语言切换提示 - 使用目标语言的翻译，确保用户能理解
      setTimeout(() => {
        const toastMessage = `${translations['language.toast'][newLanguage]}${languageNames[newLanguage]}`;

        // 确定toast样式
        const toastClass = document.documentElement.classList.contains('dark')
          ? 'bg-gray-800 text-white border border-gray-700'
          : 'bg-white text-gray-900 border border-gray-200';

        toast(toastMessage, {
          position: 'top-center',
          duration: 2000,
          className: toastClass
        });
      }, 0);
    }
  };

  return {
    language,
    setLanguage: setLanguageDirect, // 直接设置语言，不显示toast
    toggleLanguage, // 带提示的语言切换
    languageName: languageNames[language],
    supportedLanguages: Object.keys(languageNames) as Language[],
    t, // 翻译函数
    updateCounter // 用于强制重新渲染的计数器
  };
}
