# Ontology 使用说明 - 再生能源与城市廢棄物熱裂解

**创建日期**: 2026-01-03
**创建人**: Daniel Chung
**最后修改日期**: 2026-01-03

---

## 📋 概述

本文档说明如何使用新创建的再生能源领域 Ontology 和城市廢棄物熱裂解专业 Ontology 进行知识图谱提取测试。

---

## 🎯 创建的 Ontology

### 1. Domain Ontology: 再生能源

**文件**: `kag/ontology/domain-renewable-energy.json`

**Ontology 名称**: `Renewable_Energy_Domain_Ontology`

**版本**: 1.0

**继承**: `5W1H_Base_Ontology_OWL`

**核心实体类别** (10个):

1. **Renewable_Energy_Source** - 再生能源來源（太陽能、風能、水力等）
2. **Energy_Generation_Facility** - 能源發電設施
3. **Energy_Storage_System** - 能源儲存系統
4. **Energy_Conversion_Process** - 能源轉換過程
5. **Energy_Output** - 能源輸出（電力、熱能、燃料）
6. **Energy_Efficiency_Metric** - 能源效率指標
7. **Environmental_Impact** - 環境影響
8. **Energy_Policy** - 能源政策
9. **Research_Project** - 研究專案
10. **Technology_Innovation** - 技術創新

**核心关系类型** (10个):

- `generates` - 產生能源輸出
- `converts_to` - 能源轉換
- `stores` - 儲存能源
- `has_efficiency` - 具有效率指標
- `causes_impact` - 造成環境影響
- `regulated_by` - 受政策規範
- `uses_technology` - 使用技術創新
- `located_at` - 位於地點
- `operated_by` - 由組織運營
- `researches` - 研究特定主題

---

### 2. Major Ontology: 城市廢棄物熱裂解

**文件**: `kag/ontology/major-waste-pyrolysis.json`

**Ontology 名称**: `Waste_Pylysis_Major_Ontology`

**版本**: 1.0

**继承**: `5W1H_Base_Ontology_OWL`, `Renewable_Energy_Domain_Ontology`

**核心实体类别** (15个):

1. **Waste_Material** - 城市廢棄物材料
2. **Pyrolysis_Reactor** - 熱裂解反應器
3. **Pyrolysis_Process** - 熱裂解過程
4. **Pyrolysis_Product** - 熱裂解產物
5. **Biochar** - 生物炭
6. **Bio_Oil** - 生物油
7. **Syngas** - 合成氣
8. **Pyrolysis_Temperature** - 熱裂解溫度
9. **Residence_Time** - 停留時間
10. **Feedstock_Composition** - 原料組成
11. **Waste_Collection_Facility** - 廢棄物收集設施
12. **Pyrolysis_Plant** - 熱裂解廠
13. **Emission_Control_System** - 排放控制系統
14. **Product_Application** - 產物應用
15. **Process_Parameter** - 製程參數

**核心关系类型** (13个):

- `processes` - 處理廢棄物
- `produces` - 產生產物
- `operates_at` - 在特定溫度下運作
- `requires_time` - 需要停留時間
- `has_composition` - 具有組成
- `collected_from` - 從收集設施取得
- `contains` - 包含設備
- `controls_emission` - 控制排放
- `used_for` - 用於特定應用
- `has_parameter` - 具有製程參數
- `affects_yield` - 影響產率
- `converts_to_energy` - 轉換為能源
- `sequesters_carbon` - 碳封存

---

## 🔧 使用方法

### 方法 1: 自动选择（推荐）

系统会根据文件名和内容自动选择 Ontology：

```python
# 在文件上传时，系统会自动：
# 1. 分析文件名（如包含"廢棄物"、"熱裂解"等关键词）
# 2. 分析文件内容预览
# 3. 自动选择 domain-renewable-energy.json 和 major-waste-pyrolysis.json
```

**触发关键词**:
- **Domain**: "再生能源", "新能源", "太陽能", "風能", "生質能", "能源", "發電"
- **Major**: "廢棄物", "熱裂解", "城市廢棄物", "生物炭", "生物油", "合成氣"

### 方法 2: 手动指定

在 API 调用时手动指定 Ontology：

```python
# 在 kg_extraction_service 的 options 中指定
options = {
    "ontology": {
        "domain": ["domain-renewable-energy.json"],
        "major": "major-waste-pyrolysis.json"
    },
    "use_ontology": True
}
```

### 方法 3: 仅使用 Domain Ontology

如果文件只涉及再生能源，不涉及热裂解：

```python
options = {
    "ontology": {
        "domain": ["domain-renewable-energy.json"],
        "major": None
    },
    "use_ontology": True
}
```

---

## 📊 验证结果

**测试结果**:

```
✅ Domain Ontology 加载成功
   - 实体类别数量: 28 (Base + Domain)
   - 关系类型数量: 41 (Base + Domain)

✅ 完整 Ontology (Domain + Major) 加载成功
   - 实体类别数量: 43 (Base + Domain + Major)
   - 关系类型数量: 52 (Base + Domain + Major)
   - 关键实体: ['Waste_Material', 'Pyrolysis_Reactor', 'Pyrolysis_Process', 'Biochar', 'Bio_Oil', 'Syngas']
```

---

## 📝 测试建议

### 测试文件内容建议

**适合测试的文档内容**:

1. **城市廢棄物熱裂解技術文檔**:
   - 描述廢棄物熱裂解過程
   - 提及反應器、溫度、產物等
   - 包含生物炭、生物油、合成氣等產物

2. **再生能源發電設施文檔**:
   - 描述太陽能、風能發電設施
   - 提及能源轉換、儲存系統
   - 包含效率指標、環境影響

3. **廢棄物轉能源專案報告**:
   - 描述廢棄物處理流程
   - 提及熱裂解廠、製程參數
   - 包含產物應用、環境效益

### 预期提取的三元组示例

**示例 1**: 廢棄物熱裂解過程
```
主體: 城市廢棄物 (Waste_Material)
關係: processes
客體: 熱裂解反應器 (Pyrolysis_Reactor)
```

**示例 2**: 產物生成
```
主體: 熱裂解過程 (Pyrolysis_Process)
關係: produces
客體: 生物炭 (Biochar)
```

**示例 3**: 產物應用
```
主體: 生物炭 (Biochar)
關係: used_for
客體: 土壤改良 (Product_Application)
```

---

## 🔍 检查清单

在测试前，请确认：

- [ ] Ontology 文件已创建（`domain-renewable-energy.json`, `major-waste-pyrolysis.json`）
- [ ] `ontology_list.json` 已更新
- [ ] JSON 格式验证通过
- [ ] Ontology 可以正确加载
- [ ] 测试文件包含相关关键词或内容

---

## 📚 相关文档

- [Ontology 系统](./Ontology系统.md) - Ontology 系统架构详解
- [Ontology 选择策略](./Ontology选择策略-优先级降级fallback实现说明.md) - Ontology 选择策略实现说明
- [文件上傳功能架構說明](./文件上傳向量圖譜/上傳的功能架構說明-v3.0.md) - 文件上传和知识图谱提取流程

---

## 🎯 下一步

1. **准备测试文件**: 准备一个关于城市廢棄物熱裂解或再生能源的文档
2. **上传文件**: 通过文件上传 API 上传测试文件
3. **检查 Ontology 选择**: 查看日志确认系统是否正确选择了 Ontology
4. **验证提取结果**: 检查提取的三元组是否符合预期
5. **调整 Prompt**: 如果提取结果不理想，可以调整 Prompt 模板

---

**创建完成！** 现在可以使用这些 Ontology 进行知识图谱提取测试了。

