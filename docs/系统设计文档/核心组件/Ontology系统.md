# Ontology 系统架构文档

**创建日期**: 2025-12-25
**创建人**: Daniel Chung
**最后修改日期**: 2025-12-25

---

## 📋 概述

Ontology（本体）系统是 AI-Box 知识图谱的核心结构化定义，采用**3-tier（三层）架构**，用于约束实体类型和关系类型。Ontology 系统确保了知识提取的精确性和一致性，同时支持多租户与动态扩展。

> **相关文档**：
>
> - [文件上传架构说明](./文件上傳向量圖譜/上傳的功能架構說明-v2.0.md) - Ontology 系统详解章节
> - [知识图谱系统](./知识图谱系统.md) - Ontology 在知识图谱中的应用

---

## 🏗️ 架构设计

### 3-tier 架构理念

AI-Box Ontology 系统采用**三层架构**，平衡了全面性与专业性，避免过多层级的复杂性：

```
┌─────────────────────────────────────────────────────────┐
│  Major Layer（专业层）                                   │
│  - 特定专业的实体和关系                                   │
│  - 例如：Manufacture, NotionEditor                      │
└─────────────────────────────────────────────────────────┘
                        ↑ 扩展
┌─────────────────────────────────────────────────────────┐
│  Domain Layer（领域层）                                  │
│  - 特定领域的实体和关系                                   │
│  - 例如：Enterprise, Administration                     │
└─────────────────────────────────────────────────────────┘
                        ↑ 扩展
┌─────────────────────────────────────────────────────────┐
│  Base Layer（基础层）                                    │
│  - 通用基础实体（5W1H框架）                              │
│  - 例如：Person, Organization, TimePoint, Location      │
└─────────────────────────────────────────────────────────┘
```

### 架构优势

1. **层次清晰**：Base → Domain → Major 的清晰层次，易于理解与维护
2. **避免过度复杂**：三层架构避免了过多层级的复杂性
3. **支持扩展**：企业可以根据实际专业需求进行扩展
4. **全面专业**：既能保证全面性（Base层通用概念），又能保证专业性（Major层专业概念）

---

## 🔧 核心组件

### Base Layer（基础层）

**定位**：通用基础实体定义

**核心实体**：基于 **5W1H 框架**（Who, What, When, Where, Why, How）

- **Who**：Person, Organization, Role 等
- **What**：Event, Task, Product 等
- **When**：TimePoint, Period, Deadline 等
- **Where**：Location, Place, Address 等
- **Why**：Reason, Purpose, Goal 等
- **How**：Method, Process, Procedure 等

**特点**：

- 所有知识图谱提取任务都必须载入此基础 Ontology
- 提供通用实体类型与关系类型定义
- 作为 Domain 和 Major 层的基础

**实现状态**：✅ **已实现**

- 文件：`kag/ontology/base.json`
- Ontology名称：`5W1H_Base_Ontology_OWL`
- 版本：3.0

### Domain Layer（领域层）

**定位**：特定领域的实体和关系定义

**示例领域**：

- **Enterprise**：企业领域（公司、部门、职位等）
- **Administration**：管理领域（流程、决策、授权等）

**特点**：

- 扩展 Base 层的通用概念
- 提供领域特定的实体类型与关系类型
- 可以组合多个 Domain Ontology

**实现状态**：✅ **已实现**

- 示例：`kag/ontology/domain-enterprise.json`
- 支持多租户，每个租户可以有自己专属的 Domain Ontology

### Major Layer（专业层）

**定位**：特定专业的实体和关系定义

**示例专业**：

- **Manufacture**：制造业专业（生产、质量、供应链等）
- **NotionEditor**：Notion编辑器专业（页面、数据库、块等）

**特点**：

- 扩展 Domain 层的领域概念
- 提供专业特定的实体类型与关系类型
- 一个文件只能选择一个 Major Ontology（与 Domain 兼容性检查）

**实现状态**：✅ **已实现**

- 示例：`kag/ontology/major-manufacture.json`
- 支持多租户，每个租户可以有自己专属的 Major Ontology

---

## 💾 存储架构

### ArangoDB 存储

**Collection**：`ontologies`

**数据模型**：

```python
{
    "_key": "{type}-{name}-{version}" 或 "{type}-{name}-{version}-{tenant_id}",
    "tenant_id": Optional[str],  # null 表示全局共享
    "type": "base" | "domain" | "major",
    "name": str,  # Ontology 名称
    "version": str,  # 语义化版本（如 "1.0.0"）
    "default_version": bool,  # 是否为默认版本
    "ontology_name": str,  # 完整 Ontology 名称
    "entity_classes": List[EntityClass],  # 实体类别列表
    "object_properties": List[ObjectProperty],  # 物件属性列表
    "is_active": bool,  # 是否启用
    "created_at": str,  # ISO 8601 格式
    "updated_at": str,  # ISO 8601 格式
    # ... 其他元数据
}
```

### 存储服务

**服务**：`OntologyStoreService`

- **文件**：`services/api/services/ontology_store_service.py`
- **功能**：
  - Ontology CRUD 操作
  - 多租户支持（租户专属 Ontology）
  - 版本管理
  - Ontology 合并

### 查询优先级

**方法**：`get_ontology_with_priority`

**优先级**：租户专属 > 全局共享

**查询逻辑**：

1. 先查询租户专属的默认版本
2. 如果不存在，再查询全局共享的默认版本
3. 如果不存在，查询指定版本

---

## 🔄 Ontology 合并机制

### 合并顺序

**顺序**：Base → Domain → Major

1. **Base Layer**：载入基础 Ontology（必需）
2. **Domain Layer**：载入领域 Ontology（可多个，扩展 Base）
3. **Major Layer**：载入专业 Ontology（一个，扩展 Domain）

### 合并逻辑

**文件系统模式**（向后兼容）：

- 位置：`kag/kag_schema_manager.py`
- 从 JSON 文件读取并合并

**ArangoDB 模式**（推荐）：

- 位置：`services/api/services/ontology_store_service.py`
- 从 ArangoDB 查询并合并
- 支持多租户与版本管理

### 合并示例

```python
# 1. 载入 base ontology
base_ontology = store_service.get_ontology_with_priority(
    "5W1H_Base_Ontology_OWL", "base", tenant_id
)

# 2. 载入 domain ontologies
for domain_file in domain_files:
    domain_ontology = store_service.get_matching_ontology(
        domain_file, "domain", tenant_id
    )
    # 合并实体和关系...

# 3. 载入 major ontology
if major_file:
    major_ontology = store_service.get_matching_ontology(
        major_file, "major", tenant_id
    )
    # 合并实体和关系...
```

---

## 🎯 在知识图谱提取中的应用

### 自动选择机制

**选择器**：`OntologySelector`

**位置**：`kag/ontology_selector.py`

**方法**：`select_auto(file_name, file_content, file_metadata)`

**选择策略**：

1. 从文件名提取关键字
2. 从文件内容预览（前1000字符）提取关键字
3. 从元数据提取文档类型
4. 匹配 `ontology_list.json` 中的关键字索引
5. 验证 Major 与 Domain 的兼容性

### 应用流程

```
文件上传
    ↓
OntologySelector.select_auto()
    ├── 提取关键字
    ├── 匹配 Ontology
    └── 验证兼容性
    ↓
合并 Ontology（Base + Domain + Major）
    ↓
知识图谱提取服务使用合并后的 Ontology
    ├── 实体类型约束
    ├── 关系类型约束
    └── 属性范围约束
    ↓
生成三元组（NER/RE/RT）
```

---

## 📊 多租户支持

### 租户隔离

**策略**：

- 全局共享 Ontology：`tenant_id = null`
- 租户专属 Ontology：`tenant_id = <tenant_id>`

**查询优先级**：

1. 优先查询租户专属的 Ontology
2. 如果不存在，使用全局共享的 Ontology

### 扩展支持

**企业扩展**：

- 企业可以创建自己的 Domain 或 Major Ontology
- 存储时设置 `tenant_id`，实现租户隔离
- 支持版本管理，可以保留历史版本

---

## 📊 实现状态

### 已完成功能

| 功能模块 | 状态 | 说明 |
|---------|------|------|
| Base Layer | ✅ 已实现 | 5W1H 基础 Ontology |
| Domain Layer | ✅ 已实现 | Enterprise 等领域 Ontology |
| Major Layer | ✅ 已实现 | Manufacture、NotionEditor 等专业 Ontology |
| ArangoDB 存储 | ✅ 已实现 | OntologyStoreService |
| Ontology 合并 | ✅ 已实现 | Base → Domain → Major 合并逻辑 |
| 自动选择机制 | ✅ 已实现 | OntologySelector |
| 多租户支持 | ✅ 已实现 | 租户专属 Ontology |

### 进行中功能

| 功能模块 | 状态 | 说明 |
|---------|------|------|
| 更多 Domain Ontology | 🔄 进行中 | 扩展更多领域支持 |
| 更多 Major Ontology | 🔄 进行中 | 扩展更多专业支持 |

---

## 🗺️ 开发进度

### 阶段四完成情况

根据 [项目控制表](../../../開發過程文件/項目控制表.md)，**阶段四：数据处理阶段**已完成：

- ✅ **Ontology 存储与查询**（已完成）
  - ArangoDB 存储实现
  - OntologyStoreService 实现
  - 多租户支持

- ✅ **Ontology 合并机制**（已完成）
  - Base → Domain → Major 合并逻辑
  - 文件系统模式（向后兼容）
  - ArangoDB 模式（推荐）

- ✅ **Ontology 自动选择**（已完成）
  - OntologySelector 实现
  - 关键字匹配机制
  - 兼容性验证

---

## 🎯 未来发展方向

### 短期目标（1-2个月）

1. **扩展 Domain Ontology**：增加更多领域支持（如医疗、金融等）
2. **扩展 Major Ontology**：增加更多专业支持
3. **Ontology 版本管理增强**：支持更灵活的版本管理策略

### 中期目标（3-6个月）

1. **Ontology 编辑器**：提供图形化的 Ontology 编辑工具
2. **Ontology 验证工具**：自动验证 Ontology 的一致性与完整性
3. **Ontology 导入导出**：支持标准格式（如 OWL）的导入导出

### 长期目标（6-12个月）

1. **Ontology 推荐系统**：基于文件内容智能推荐合适的 Ontology
2. **Ontology 学习**：从知识图谱中自动学习新的 Ontology 概念
3. **Ontology 生态**：构建 Ontology 分享与协作生态

---

## 📚 参考资料

### 相关文档

- [文件上传架构说明](./文件上傳向量圖譜/上傳的功能架構說明-v2.0.md) - Ontology 系统详解
- [知识图谱系统](./知识图谱系统.md) - Ontology 在知识图谱提取中的应用

### 代码位置

- Ontology 存储服务：`services/api/services/ontology_store_service.py`
- Ontology 管理器：`kag/kag_schema_manager.py`
- Ontology 选择器：`kag/ontology_selector.py`
- Ontology 数据模型：`services/api/models/ontology.py`
- Ontology 列表：`kag/ontology/ontology_list.json`

---

**最后更新日期**: 2025-12-25
