<!-- 7f8029d4-8f20-4d06-ae76-818cf9d11195 d418ec6d-5ba5-46eb-a56b-e5037f684ed1 -->
# 修复 AI-Box 文件上传后台功能缺失

## 问题分析

### 架构规划要求（DIRECTORY_STRUCTURE.md）

根据架构文档，文件上传功能应包含：

- `api/routers/file_upload.py` - 文件上传路由 ✅ 已存在
- `genai/api/routers/chunk_processing.py` - 文件分块处理路由 ✅ 已存在
- `services/api/processors/` - 文件处理器模块 ❌ **缺失**

### 当前状态

- ✅ API路由层完整（`api/routers/file_upload.py`, `api/routers/file_management.py`）
- ✅ 服务层完整（`services/api/services/embedding_service.py`, `vector_store_service.py`, `kg_extraction_service.py`）
- ✅ 存储层完整（`storage/file_storage.py`）
- ✅ 数据库层完整（`database/chromadb/`, `database/arangodb/`, `database/redis/`）
- ❌ **处理器模块缺失**（`services/api/processors/`）

### 依赖关系

`genai/api/routers/chunk_processing.py` 第17-24行导入：

```python
from services.api.processors.chunk_processor import ChunkProcessor, create_chunk_processor_from_config
from services.api.processors.parsers.txt_parser import TxtParser
from services.api.processors.parsers.md_parser import MdParser
from services.api.processors.parsers.pdf_parser import PdfParser
from services.api.processors.parsers.docx_parser import DocxParser
```

这些模块在 `backup/refactoring/services/api/processors/` 中存在完整代码。

## 修复计划

### 步骤 1: 恢复 processors 模块

从备份目录复制完整的 `processors` 模块到正确位置：

- 复制 `backup/refactoring/services/api/processors/` → `services/api/processors/`
- 包含以下文件：
  - `__init__.py`
  - `chunk_processor.py` - 文件分块处理器（支持固定大小、滑动窗口、语义分块）
  - `parser_factory.py` - 解析器工厂
  - `parsers/__init__.py`
  - `parsers/base_parser.py` - 解析器基类
  - `parsers/txt_parser.py` - 文本解析器
  - `parsers/md_parser.py` - Markdown解析器
  - `parsers/pdf_parser.py` - PDF解析器（依赖 PyPDF2）
  - `parsers/docx_parser.py` - DOCX解析器（依赖 python-docx）
  - `parsers/csv_parser.py` - CSV解析器
  - `parsers/json_parser.py` - JSON解析器
  - `parsers/html_parser.py` - HTML解析器
  - `parsers/xlsx_parser.py` - XLSX解析器

### 步骤 2: 验证导入路径

检查并修复可能的导入问题：

- 确认 `chunk_processor.py` 中的导入路径正确
- 确认 `parser_factory.py` 中的导入路径正确
- 确认所有 parsers 中的 `from .base_parser import BaseParser` 正确

### 步骤 3: 检查配置依赖

验证 `chunk_processor.py` 中的 `create_chunk_processor_from_config` 函数：

- 确认配置读取逻辑正确（使用 `system.infra.config.config.get_config_section`）
- 确认默认配置值合理

### 步骤 4: 验证文件上传流程

测试完整的文件上传流程：

1. 前端上传文件 → `api/routers/file_upload.py`
2. 文件验证和保存
3. 触发后台处理 → 调用 `genai/api/routers/chunk_processing.py`
4. 文件解析 → 使用 `services.api.processors.parsers.*`
5. 文件分块 → 使用 `services.api.processors.chunk_processor.ChunkProcessor`
6. 向量化和存储
7. KG提取和存储

### 步骤 5: 更新文档

如有必要，更新相关文档说明 processors 模块的位置和功能。

## 文件清单

### 需要创建的文件

- `services/api/processors/__init__.py`
- `services/api/processors/chunk_processor.py`
- `services/api/processors/parser_factory.py`
- `services/api/processors/parsers/__init__.py`
- `services/api/processors/parsers/base_parser.py`
- `services/api/processors/parsers/txt_parser.py`
- `services/api/processors/parsers/md_parser.py`
- `services/api/processors/parsers/pdf_parser.py`
- `services/api/processors/parsers/docx_parser.py`
- `services/api/processors/parsers/csv_parser.py`
- `services/api/processors/parsers/json_parser.py`
- `services/api/processors/parsers/html_parser.py`
- `services/api/processors/parsers/xlsx_parser.py`

### 参考文件（备份位置）

- `backup/refactoring/services/api/processors/`（所有文件）

## 注意事项

1. **代码头部注释**：复制文件时需更新创建日期和最后修改日期（使用当前时间）
2. **依赖检查**：确保 PDF 和 DOCX 解析器的可选依赖（PyPDF2, python-docx）在导入时有正确的错误处理
3. **配置验证**：确认 `chunk_processor.py` 中的配置读取逻辑与项目配置系统兼容
4. **测试验证**：修复后应运行测试确保文件上传功能正常工作

### To-dos

- [ ] 从 backup/refactoring/services/api/processors/ 复制完整的 processors 模块到 services/api/processors/
- [ ] 验证所有导入路径正确，特别是相对导入和绝对导入
- [ ] 检查 chunk_processor.py 中的配置读取逻辑是否正确使用 system.infra.config.config.get_config_section
- [ ] 测试完整的文件上传流程，确保从文件上传到分块处理都能正常工作
- [ ] 如有必要，更新相关文档说明 processors 模块的位置和功能
