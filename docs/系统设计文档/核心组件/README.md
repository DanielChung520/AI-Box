# 核心组件文档索引

**创建日期**: 2025-12-25
**创建人**: Daniel Chung
**最后修改日期**: 2026-01-21

---

## 📚 核心组件文档列表

本文档目录包含 AI-Box 系统各核心组件的详细架构文档：

### 后端核心组件

1. **[Agent Platform](./Agent-Platform.md)** - Agent平台三层架构详解
2. **[AAM系统](./AAM系统.md)** - 长短记忆上下文架构
3. **[文件上传架构说明](./文件上傳向量圖譜/上傳的功能架構說明-v4.0.md)** - 文件处理流程详解（整合文件管理、状态管理、文件存储系统）
4. **[双轨 RAG 解析系统](./文件上傳向量圖譜/AI-Box雙軌RAG解析規格書.md)** - 双轨 RAG 架构详解（Stage 1 快速轨 + Stage 2 深度轨）
5. **[双轨 RAG 实施计划](./文件上傳向量圖譜/AI-Box雙軌RAG解析實施計劃書.md)** - 实施进度管控表和状态说明
6. **[强化RAG系统](./文件上傳向量圖譜/强化RAG系统.md)** - ChromaDB向量化与语义切片
7. **[知识图谱系统](./文件上傳向量圖譜/知识图谱系统.md)** - ArangoDB图存储与NER/RE/RT提取
6. **[Ontology系统](./文件上傳向量圖譜/Ontology系统.md)** - 3-tier架构（base/domain/major）
7. **[Ontology选择策略](./文件上傳向量圖譜/Ontology选择策略-优先级降级fallback实现说明.md)** - Ontology选择策略实现说明
8. **[文件上传向量图谱化测试计划](./文件上傳向量圖譜/文件上傳向量圖譜化測試計劃.md)** - 测试计划和验证方法
9. **[MoE系统](./MoE系统.md)** - Multi-model专家模型架构
10. **[MCP工具系统](./MCP工具/)** - Model Context Protocol 工具系统
    - [MCP工具系统规格](./MCP工具/MCP工具.md) - 工具系统详细规格
    - [Cloudflare MCP Gateway 设置指南](./MCP工具/Cloudflare-MCP-Gateway-设置指南.md) - Gateway 设置指南
11. **[生成式AI链式处理系统](./生成式AI链式处理系统.md)** - System prompt与文件处理流程
12. **[存储架构](./存储架构.md)** - ArangoDB、ChromaDB、SeaweedFS 双服务完整配置说明

### 系统管理组件

13. **[部署架构](./系統管理/部署架构.md)** - 混合部署、k8s、Redis Worker、系统参数配置策略
14. **[部署架构-参数策略符合性检核](./系統管理/部署架构-参数策略符合性检核.md)** - 参数使用策略符合性检核报告
15. **[负载均衡器API文档](./系統管理/负载均衡器API文档.md)** - 负载均衡器 API 使用说明
16. **[SeaweedFS使用指南](./系統管理/SeaweedFS使用指南.md)** - SeaweedFS 使用指南和 API 示例

### 前端组件

17. **[IEE前端系统](../IEE前端系統/IEE前端系统.md)** - Intelligent Editor Environment

### 规划中组件

18. **[Personal Data / RoLA](./Personal-Data-RoLA.md)** - 个人化学习系统（规划中）

---

## 🔗 相关文档

- [系统设计文档主README](../README.md)
- [系统价值与独特性](../系统价值与独特性.md)
- [开发进度文档](../开发进度/)

---

**最后更新日期**: 2026-01-20
