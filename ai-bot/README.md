# AI 智能聊天助手应用

一个基于 React 18+ 和 TypeScript 构建的现代化 AI 聊天应用，提供智能对话、多语言支持和深色/浅色主题切换等功能。

## 🚀 技术栈

- **前端框架**: React 18+
- **编程语言**: TypeScript
- **样式系统**: Tailwind CSS
- **路由**: React Router
- **图标**: Font Awesome
- **构建工具**: Vite
- **数据可视化**: Recharts
- **图表渲染**: Mermaid
- **表单验证**: Zod
- **UI 组件**: Sonner (Toast 提示)

## ✨ 功能特性

- **智能对话**: 与多种 AI Agent 进行交互
- **多语言支持**: 英文、简体中文和繁体中文
- **深色/浅色主题**: 根据偏好或系统设置自动切换
- **文件管理**: 文件树结构和 Markdown 预览功能
- **任务管理**: 创建和跟踪聊天任务
- **数据可视化**: 支持 Mermaid 图表渲染
- **响应式设计**: 适配各种屏幕尺寸

## 🚀 快速开始

### 环境要求

- Node.js 18+
- pnpm 或 npm/yarn

### 安装依赖

```bash
# 使用 pnpm（推荐）
pnpm install

# 或使用 npm
npm install

# 或使用 yarn
yarn install
```

### 开发模式

```bash
# 使用 pnpm
pnpm dev

# 或使用 npm
npm run dev

# 或使用 yarn
yarn dev
```

应用将在 http://localhost:3000 启动。

### 构建生产版本

```bash
# 使用 pnpm
pnpm build

# 或使用 npm
npm run build

# 或使用 yarn
yarn build
```

构建后的文件将输出到 `dist` 目录。

## 📁 项目结构

```
├── src/                 # 源代码目录
│   ├── components/      # React 组件
│   ├── contexts/        # React Context
│   ├── hooks/           # 自定义 React Hooks
│   ├── lib/             # 工具函数
│   ├── pages/           # 页面组件
│   ├── App.tsx          # 应用主组件
│   ├── index.css        # 全局样式
│   └── main.tsx         # 入口文件
├── index.html           # HTML 入口
├── package.json         # 项目配置和依赖
└── vite.config.ts       # Vite 配置
```

## 📖 使用说明

### 语言切换

应用支持三种语言：英文、简体中文和繁体中文。可以通过聊天区域顶部的语言选择器切换语言。

### 主题切换

点击聊天区域顶部的太阳/月亮图标可以在深色模式和浅色模式之间切换。应用也会尊重系统的主题偏好设置。

### AI 对话

1. 从侧边栏选择一个 Agent 或创建新任务
2. 在底部输入框中输入您的问题
3. 点击发送按钮或按 Enter 键发送消息
4. AI 将生成响应，包括可能的 Mermaid 图表

### 文件管理

1. 在右侧结果面板中切换到"文件"标签
2. 浏览文件树结构
3. 点击文件可在预览视图中查看其内容

## 🛠️ 开发说明

### 组件结构

- **Sidebar**: 左侧边栏，包含收藏夹、任务、助理和代理
- **ChatArea**: 中间聊天区域，显示对话内容和 Agent 卡片
- **ResultPanel**: 右侧结果面板，提供文件浏览和 Markdown 预览

### 自定义 Hooks

- **useLanguage**: 语言管理和翻译功能
- **useTheme**: 主题切换和管理功能

### 主题和样式

项目使用 Tailwind CSS 进行样式管理，并在 `index.css` 中定义了主题变量。主题切换通过添加/移除 `light` 类到 `document.documentElement` 实现。

## 📝 许可证

MIT License

## 🤝 贡献

欢迎提交问题和改进建议！

---

© 2025 AI 智能聊天助手团队
