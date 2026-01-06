# NER/RE/RT Ontology 集成问题分析

**创建日期**: 2026-01-01
**创建人**: Daniel Chung
**最后修改日期**: 2026-01-01

---

## 📋 问题概述

当前NER/RE/RT服务的实现**没有使用Ontology信息**，而是使用硬编码的实体类型和关系类型，**不符合通过LLM语义匹配Ontology的设计理念**。

---

## 🔍 当前实现分析

### 1. NER Service (`genai/api/services/ner_service.py`)

**当前实现**：
- 使用硬编码的实体类型：`PERSON`, `ORG`, `LOC`, `DATE`, `MONEY`, `PRODUCT`, `EVENT`
- Prompt模板中没有包含Ontology信息：
  ```python
  self._prompt_template = """請從以下文本中識別命名實體，並以 JSON 格式返回結果。
  文本：{text}
  
  請返回 JSON 格式，包含以下字段：
  - text: 實體文本
  - label: 實體類型（PERSON, ORG, LOC, DATE, MONEY, PRODUCT, EVENT 等）
  ...
  """
  ```

**问题**：
- ❌ 没有接收Ontology的`entity_classes`列表
- ❌ Prompt中没有注入Ontology的实体类型
- ❌ LLM无法通过语义匹配Ontology中的实体类型

### 2. RE Service (`genai/api/services/re_service.py`)

**当前实现**：
- 提取关系时未使用Ontology的`relationship_types`
- 未使用OWL Domain/Range约束

**问题**：
- ❌ 没有接收Ontology的`relationship_types`列表
- ❌ Prompt中没有注入Ontology的关系类型
- ❌ 没有OWL Domain/Range约束信息

### 3. RT Service (`genai/api/services/rt_service.py`)

**当前实现**：
- 关系分类时未使用Ontology的`relationship_types`

**问题**：
- ❌ 没有接收Ontology的`relationship_types`列表
- ❌ Prompt中没有注入Ontology的关系类型

---

## ✅ 正确的设计（参考Prompt-Template.json）

根据`kag/ontology/Prompt-Template.json`和`kag/kag_schema_manager_v2.py`的设计，正确的实现应该是：

### 1. Prompt应该包含Ontology信息

```json
{
  "instruction_template": [
    "### 1. 核心實體類型 (Entity Classes):",
    "[INJECT_ENTITY_LIST]",
    "### 2. 關係類型約束 (Relationship Types):",
    "[INJECT_RELATIONSHIP_LIST]",
    "### 3. OWL Domain/Range 規則 (嚴格約束):",
    "提取的三元組必須滿足 Domain-Range 約束。",
    ...
  ]
}
```

### 2. NER Service应该接收Ontology信息

**正确的接口**：
```python
async def extract_entities(
    self,
    text: str,
    ontology_rules: Optional[Dict[str, Any]] = None,  # 新增
    user_id: Optional[str] = None,
    file_id: Optional[str] = None,
    task_id: Optional[str] = None,
) -> List[Entity]:
    """提取實體"""
    # 生成包含Ontology信息的prompt
    prompt = self._generate_prompt_with_ontology(text, ontology_rules)
    ...
```

**Prompt应该包含**：
- Ontology的`entity_classes`列表（从合并后的Ontology中获取）
- 每个实体类的描述（如果可用）
- OWL约束信息（如果可用）

### 3. RE Service应该接收Ontology信息

**正确的接口**：
```python
async def extract_relations(
    self,
    text: str,
    entities: List[Entity],
    ontology_rules: Optional[Dict[str, Any]] = None,  # 新增
) -> List[Relation]:
    """提取關係"""
    # 生成包含Ontology信息的prompt
    prompt = self._generate_prompt_with_ontology(text, entities, ontology_rules)
    ...
```

**Prompt应该包含**：
- Ontology的`relationship_types`列表
- OWL Domain/Range约束（哪些实体类型可以使用哪些关系类型）

### 4. RT Service应该接收Ontology信息

**正确的接口**：
```python
async def classify_relation_type(
    self,
    relation: Relation,
    ontology_rules: Optional[Dict[str, Any]] = None,  # 新增
) -> List[RelationType]:
    """分類關係類型"""
    # 生成包含Ontology信息的prompt
    prompt = self._generate_prompt_with_ontology(relation, ontology_rules)
    ...
```

**Prompt应该包含**：
- Ontology的`relationship_types`列表
- OWL Domain/Range约束

---

## 🔧 集成点分析

### KG Extraction Service已经加载了Ontology

在`services/api/services/kg_extraction_service.py`的`extract_triples_from_chunks`方法中：

```python
# 載入 Ontology（如果啟用）
ontology_rules = None
if use_ontology and ONTOLOGY_SUPPORT:
    ontology_rules = self._load_ontology_for_extraction(...)

# 调用triple_service
triples = await self.triple_service.extract_triples(
    text=full_text, entities=None, enable_ner=True
)
```

**问题**：`ontology_rules`被加载了，但**没有传递给`triple_service.extract_triples()`**。

### Triple Extraction Service需要接收Ontology

`genai/api/services/triple_extraction_service.py`的`extract_triples`方法：

```python
async def extract_triples(
    self,
    text: str,
    entities: Optional[List[Entity]] = None,
    enable_ner: bool = True,
) -> List[Triple]:
    """提取三元組"""
    # 步驟 1: NER（實體識別）
    if entities is None and enable_ner:
        entities = await self.ner_service.extract_entities(text)  # ❌ 没有传递ontology_rules
    
    # 步驟 2: RE（關係抽取）
    relations = await self.re_service.extract_relations(text, entities)  # ❌ 没有传递ontology_rules
    
    # 步驟 3: RT（關係分類）
    # ...
```

**问题**：`extract_triples`方法**没有接收`ontology_rules`参数**，也没有传递给NER/RE/RT服务。

---

## 🎯 解决方案

### 方案1：修改Triple Extraction Service（推荐）

1. **修改`extract_triples`方法签名**：
   ```python
   async def extract_triples(
       self,
       text: str,
       entities: Optional[List[Entity]] = None,
       enable_ner: bool = True,
       ontology_rules: Optional[Dict[str, Any]] = None,  # 新增
   ) -> List[Triple]:
   ```

2. **将`ontology_rules`传递给NER/RE/RT服务**：
   ```python
   # NER
   entities = await self.ner_service.extract_entities(
       text, 
       ontology_rules=ontology_rules  # 新增
   )
   
   # RE
   relations = await self.re_service.extract_relations(
       text, 
       entities,
       ontology_rules=ontology_rules  # 新增
   )
   
   # RT
   relation_types = await self.rt_service.classify_relation_type(
       relation,
       ontology_rules=ontology_rules  # 新增
   )
   ```

3. **修改KG Extraction Service**：
   ```python
   triples = await self.triple_service.extract_triples(
       text=full_text, 
       entities=None, 
       enable_ner=True,
       ontology_rules=ontology_rules  # 新增
   )
   ```

### 方案2：修改NER/RE/RT Service的Prompt生成

1. **NER Service**：
   - 修改`extract_entities`方法接收`ontology_rules`
   - 修改`_prompt_template`或添加`_generate_prompt_with_ontology`方法
   - 将Ontology的`entity_classes`注入到prompt中

2. **RE Service**：
   - 修改`extract_relations`方法接收`ontology_rules`
   - 将Ontology的`relationship_types`和OWL约束注入到prompt中

3. **RT Service**：
   - 修改`classify_relation_type`方法接收`ontology_rules`
   - 将Ontology的`relationship_types`注入到prompt中

### 方案3：使用OntologyManager生成Prompt（推荐）

参考`kag/kag_schema_manager_v2.py`中的`generate_prompt`方法：

```python
def generate_prompt(
    self,
    text_chunk: str,
    ontology_rules: Optional[Dict[str, Any]] = None,
    include_owl_constraints: bool = True,
) -> str:
    """根據合併後的 Ontology 規則生成提示詞"""
    # 使用Prompt-Template.json模板
    # 注入entity_classes和relationship_types
    # 包含OWL约束
```

NER/RE/RT服务应该调用`OntologyManager.generate_prompt()`来生成包含Ontology信息的prompt。

---

## 📊 影响分析

### 当前问题的影响

1. **实体类型不匹配**：
   - LLM提取的实体类型（如`PERSON`, `ORG`）可能不在Ontology中
   - 导致知识图谱构建时类型不匹配

2. **关系类型不匹配**：
   - LLM提取的关系类型可能不在Ontology中
   - 导致知识图谱构建时关系类型无效

3. **不符合OWL约束**：
   - 没有Domain/Range约束，可能导致无效的三元组
   - 例如：`(Person, produces, Product)`可能不符合OWL约束

4. **无法利用Ontology的语义信息**：
   - Ontology中定义的实体类和关系类型没有被利用
   - LLM无法通过语义理解选择合适的Ontology类型

### 修复后的预期效果

1. **实体类型匹配**：
   - LLM从Ontology的`entity_classes`中选择合适的类型
   - 确保提取的实体类型都在Ontology中

2. **关系类型匹配**：
   - LLM从Ontology的`relationship_types`中选择合适的类型
   - 确保提取的关系类型都在Ontology中

3. **符合OWL约束**：
   - Prompt中包含Domain/Range约束
   - LLM提取的三元组符合OWL规范

4. **语义匹配**：
   - LLM通过语义理解文档内容
   - 从Ontology中选择最合适的实体类和关系类型

---

## 🔄 实施步骤

1. **修改NER Service**：
   - [ ] 添加`ontology_rules`参数
   - [ ] 修改prompt生成逻辑
   - [ ] 使用`OntologyManager.generate_prompt()`或类似的prompt生成方法

2. **修改RE Service**：
   - [ ] 添加`ontology_rules`参数
   - [ ] 修改prompt生成逻辑
   - [ ] 包含OWL Domain/Range约束

3. **修改RT Service**：
   - [ ] 添加`ontology_rules`参数
   - [ ] 修改prompt生成逻辑

4. **修改Triple Extraction Service**：
   - [ ] 添加`ontology_rules`参数
   - [ ] 传递给NER/RE/RT服务

5. **修改KG Extraction Service**：
   - [ ] 将`ontology_rules`传递给`extract_triples`方法

6. **测试**：
   - [ ] 测试NER使用Ontology提取实体
   - [ ] 测试RE使用Ontology提取关系
   - [ ] 测试RT使用Ontology分类关系类型
   - [ ] 验证OWL约束是否生效

---

## 📚 参考资料

1. `kag/ontology/Prompt-Template.json` - Prompt模板设计
2. `kag/kag_schema_manager_v2.py` - `generate_prompt`方法实现
3. `services/api/services/kg_extraction_service.py` - KG提取服务（已加载Ontology）
4. `genai/api/services/triple_extraction_service.py` - 三元组提取服务
5. `genai/api/services/ner_service.py` - NER服务
6. `genai/api/services/re_service.py` - RE服务
7. `genai/api/services/rt_service.py` - RT服务

---

**最后更新日期**: 2026-01-01

