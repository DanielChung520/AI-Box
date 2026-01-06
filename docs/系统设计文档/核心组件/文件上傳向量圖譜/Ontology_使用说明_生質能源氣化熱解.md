# Ontology 使用说明 - 生質能源氣化熱解

**创建日期**: 2026-01-03
**创建人**: Daniel Chung
**最后修改日期**: 2026-01-03

---

## 📋 Ontology 概述

**Ontology 名称**: `Biomass_Gasification_Pyrolysis_Major_Ontology`

**类型**: Major Ontology（专业本体论）

**版本**: 1.0

**继承关系**:
- `5W1H_Base_Ontology_OWL`（基础本体论）
- `Renewable_Energy_Domain_Ontology`（再生能源领域本体论）

**兼容域**: `domain-renewable-energy.json`

**描述**: 生質能源氣化熱解專業本體論，專注於生質材料氣化和熱解技術、產物和處理流程。

---

## 🎯 适用场景

### 主要用途

1. **生質能源技術文檔分析**
   - 氣化製程文檔
   - 熱解製程文檔
   - 技術規格書

2. **生質材料處理**
   - 能源作物分析
   - 農業殘餘物利用
   - 木質生質材料處理
   - 藻類生質材料應用

3. **產物應用研究**
   - 合成氣應用
   - 生物油應用
   - 生物炭應用

4. **碳封存研究**
   - 生物炭碳封存
   - 環境影響評估

---

## 📊 实体类（Entity Classes）

### 核心实体类（22 个）

#### 1. 生質材料类

- **Biomass_Feedstock**（生質材料）
  - 基础类: `Material`
  - 描述: 生質材料，如木材、農作物殘餘、能源作物、有機廢棄物、藻類等

- **Energy_Crop**（能源作物）
  - 基础类: `Biomass_Feedstock`
  - 描述: 專門種植用於能源生產的作物，如柳枝稷、芒草、麻瘋樹等

- **Agricultural_Residue**（農業殘餘物）
  - 基础类: `Biomass_Feedstock`
  - 描述: 農業殘餘物，如稻草、玉米稈、甘蔗渣等農作物收穫後的殘餘物

- **Wood_Biomass**（木質生質材料）
  - 基础类: `Biomass_Feedstock`
  - 描述: 木質生質材料，如木材、木屑、樹皮、林業廢棄物等

- **Algae_Biomass**（藻類生質材料）
  - 基础类: `Biomass_Feedstock`
  - 描述: 藻類生質材料，用於氣化或熱解的微藻或大型藻類

#### 2. 反應器和設備类

- **Gasification_Reactor**（氣化反應器）
  - 基础类: `Machine_Asset`
  - 描述: 氣化反應器，用於將生質材料在高溫下轉化為合成氣的設備

- **Pyrolysis_Reactor**（熱解反應器）
  - 基础类: `Machine_Asset`
  - 描述: 熱解反應器，用於在無氧或低氧環境下將生質材料加熱分解的設備

- **Gas_Cleaning_System**（氣體淨化系統）
  - 基础类: `Asset`
  - 描述: 氣體淨化系統，用於去除合成氣中的焦油、灰分、硫化物等雜質

- **Biomass_Plant**（生質能源廠）
  - 基础类: `Energy_Generation_Facility`
  - 描述: 生質能源廠，完整的生質材料氣化或熱解處理設施

#### 3. 過程类

- **Gasification_Process**（氣化過程）
  - 基础类: `Energy_Conversion_Process`
  - 描述: 氣化過程，在控制氧氣條件下將生質材料轉化為合成氣（主要為氫氣和一氧化碳）

- **Pyrolysis_Process**（熱解過程）
  - 基础类: `Energy_Conversion_Process`
  - 描述: 熱解過程，在無氧或低氧環境下將生質材料加熱分解為生物油、合成氣和生物炭

- **Feedstock_Preparation**（原料預處理）
  - 基础类: `Process`
  - 描述: 原料預處理，如乾燥、粉碎、造粒等，影響後續轉化效率

#### 4. 產物类

- **Syngas**（合成氣）
  - 基础类: `Energy_Output`
  - 描述: 合成氣，氣化或熱解過程產生的氣體產物，主要成分為氫氣、一氧化碳、甲烷等

- **Bio_Oil**（生物油）
  - 基础类: `Energy_Output`
  - 描述: 生物油，熱解過程產生的液體產物，可用作燃料或化學原料

- **Biochar**（生物炭）
  - 基础类: `Energy_Output`
  - 描述: 生物炭，熱解過程產生的固體殘留物，可用於土壤改良、碳封存或作為燃料

#### 5. 參數和概念类

- **Gasification_Temperature**（氣化溫度）
  - 基础类: `Concept`
  - 描述: 氣化溫度，影響合成氣組成和產率的關鍵參數，通常在 700-1200°C

- **Pyrolysis_Temperature**（熱解溫度）
  - 基础类: `Concept`
  - 描述: 熱解溫度，影響產物組成和產率的關鍵參數，通常在 400-800°C

- **Gasification_Agent**（氣化劑）
  - 基础类: `Material`
  - 描述: 氣化劑，如空氣、氧氣、水蒸氣或二氧化碳，用於控制氣化過程

- **Residence_Time**（停留時間）
  - 基础类: `Duration`
  - 描述: 停留時間，生質材料在反應器中的停留時間，影響轉化效率和產物組成

- **Process_Parameter**（製程參數）
  - 基础类: `Concept`
  - 描述: 製程參數，如加熱速率、壓力、載氣流量、當量比等

- **Product_Application**（產物應用）
  - 基础类: `Concept`
  - 描述: 產物應用，如合成氣用於發電、生物油用於交通燃料、生物炭用於農業等

- **Carbon_Sequestration**（碳封存）
  - 基础类: `Concept`
  - 描述: 碳封存，生物炭在土壤中的長期儲存，實現負碳排放

---

## 🔗 关系属性（Object Properties）

### 核心关系（15 个）

1. **processes**（處理）
   - 域: `Gasification_Reactor`, `Pyrolysis_Reactor`, `Gasification_Process`, `Pyrolysis_Process`
   - 範圍: `Biomass_Feedstock`, `Energy_Crop`, `Agricultural_Residue`, `Wood_Biomass`, `Algae_Biomass`
   - 描述: 表示氣化或熱解反應器或過程處理特定生質材料

2. **produces**（產生）
   - 域: `Gasification_Process`, `Pyrolysis_Process`, `Gasification_Reactor`, `Pyrolysis_Reactor`
   - 範圍: `Syngas`, `Bio_Oil`, `Biochar`, `Energy_Output`
   - 描述: 表示氣化或熱解過程產生特定產物

3. **operates_at**（在...溫度下運行）
   - 域: `Gasification_Process`, `Pyrolysis_Process`
   - 範圍: `Gasification_Temperature`, `Pyrolysis_Temperature`
   - 描述: 表示氣化或熱解過程在特定溫度下進行

4. **uses_agent**（使用氣化劑）
   - 域: `Gasification_Process`
   - 範圍: `Gasification_Agent`
   - 描述: 表示氣化過程使用特定的氣化劑

5. **requires_time**（需要時間）
   - 域: `Gasification_Process`, `Pyrolysis_Process`
   - 範圍: `Residence_Time`
   - 描述: 表示氣化或熱解過程需要特定的停留時間

6. **requires_preparation**（需要預處理）
   - 域: `Biomass_Feedstock`, `Energy_Crop`, `Agricultural_Residue`, `Wood_Biomass`, `Algae_Biomass`
   - 範圍: `Feedstock_Preparation`
   - 描述: 表示生質材料需要特定的預處理

7. **cleans**（淨化）
   - 域: `Gas_Cleaning_System`
   - 範圍: `Syngas`
   - 描述: 表示氣體淨化系統處理特定氣體產物

8. **contains**（包含）
   - 域: `Biomass_Plant`
   - 範圍: `Gasification_Reactor`, `Pyrolysis_Reactor`, `Gas_Cleaning_System`
   - 描述: 表示生質能源廠包含特定的反應器或設備

9. **used_for**（用於）
   - 域: `Syngas`, `Bio_Oil`, `Biochar`
   - 範圍: `Product_Application`
   - 描述: 表示氣化或熱解產物用於特定應用

10. **has_parameter**（具有參數）
    - 域: `Gasification_Process`, `Pyrolysis_Process`
    - 範圍: `Process_Parameter`
    - 描述: 表示氣化或熱解過程具有特定的製程參數

11. **affects_yield**（影響產率）
    - 域: `Process_Parameter`, `Gasification_Temperature`, `Pyrolysis_Temperature`, `Residence_Time`
    - 範圍: `Energy_Efficiency_Metric`
    - 描述: 表示製程參數、溫度或停留時間影響產物產率

12. **converts_to_energy**（轉換為能源）
    - 域: `Syngas`, `Bio_Oil`
    - 範圍: `Energy_Output`
    - 描述: 表示合成氣或生物油轉換為能源

13. **sequesters_carbon**（封存碳）
    - 域: `Biochar`
    - 範圍: `Carbon_Sequestration`, `Environmental_Impact`
    - 描述: 表示生物炭具有碳封存功能

14. **located_at**（位於）
    - 域: `Biomass_Plant`
    - 範圍: `Location`
    - 描述: 表示生質能源廠位於特定地點

15. **operated_by**（由...運營）
    - 域: `Biomass_Plant`
    - 範圍: `Organization`
    - 描述: 表示生質能源廠由特定組織運營

---

## 🔍 使用示例

### 示例 1: 生質材料氣化過程

**文本**: "柳枝稷在 800°C 的氣化反應器中，使用水蒸氣作為氣化劑，產生合成氣，主要用於發電。"

**提取的三元组**:
- `(柳枝稷, is_a, Energy_Crop)`
- `(氣化反應器, is_a, Gasification_Reactor)`
- `(800°C, is_a, Gasification_Temperature)`
- `(水蒸氣, is_a, Gasification_Agent)`
- `(合成氣, is_a, Syngas)`
- `(氣化反應器, processes, 柳枝稷)`
- `(氣化過程, operates_at, 800°C)`
- `(氣化過程, uses_agent, 水蒸氣)`
- `(氣化過程, produces, 合成氣)`
- `(合成氣, used_for, 發電)`

### 示例 2: 木質生質材料熱解

**文本**: "木屑在 500°C 的熱解反應器中熱解，產生生物油、合成氣和生物炭。生物炭用於土壤改良和碳封存。"

**提取的三元组**:
- `(木屑, is_a, Wood_Biomass)`
- `(熱解反應器, is_a, Pyrolysis_Reactor)`
- `(500°C, is_a, Pyrolysis_Temperature)`
- `(生物油, is_a, Bio_Oil)`
- `(生物炭, is_a, Biochar)`
- `(熱解過程, processes, 木屑)`
- `(熱解過程, operates_at, 500°C)`
- `(熱解過程, produces, 生物油)`
- `(熱解過程, produces, 合成氣)`
- `(熱解過程, produces, 生物炭)`
- `(生物炭, used_for, 土壤改良)`
- `(生物炭, sequesters_carbon, 碳封存)`

---

## 📝 测试建议

### 测试文件类型

1. **技术文档**
   - 氣化技術規格書
   - 熱解製程手冊
   - 設備操作指南

2. **研究報告**
   - 生質能源研究報告
   - 碳封存研究
   - 產物應用研究

3. **專案文件**
   - 生質能源廠建設計劃
   - 能源作物種植計劃
   - 產物應用專案

### 测试关键词

- 生質能源、生質能
- 氣化、熱解
- 生質材料、能源作物
- 合成氣、生物油、生物炭
- 碳封存

---

## 🔗 相关 Ontology

- **Base Ontology**: `base.json`（5W1H_Base_Ontology_OWL）
- **Domain Ontology**: `domain-renewable-energy.json`（Renewable_Energy_Domain_Ontology）
- **Related Major**: `major-waste-pyrolysis.json`（城市廢棄物熱裂解）

---

## 📊 统计信息

- **实体类数量**: 22
- **关系属性数量**: 15
- **ArangoDB ID**: `major-Biomass_Gasification_Pyrolysis-1.0`
- **存储位置**: ArangoDB `ontologies` collection（系統級）

---

**创建完成时间**: 2026-01-03 23:48

