# AI-Box 系統 AI 治理規劃

**創建日期**: 2026-01-27
**創建人**: Daniel Chung
**最後修改日期**: 2026-01-27
**文檔版本**: 1.0
**狀態**: 草案，待 Review

---

## 文檔背景

本規劃基於 2026-01-25 數據丟失事件（ArangoDB 被誤重建）而制定，整合並增強了以下現有文檔：
- WBS-4: AI 治理與合規（待開始）
- WBS-階段六：AI 治理（規劃階段）
- 數據備份規範（2026-01-27 新增）

## 問題分析

### 事件概況

**時間**: 2026-01-25 12:10:51Z  
**影響範圍**: ArangoDB 所有 collections 被重置  
**丟失數據**: 17 個 collections 中的臨時數據（ontologies、model_usage、operation_logs 等）  
**根本原因**: 
1. Docker volume `ai-box_arangodb_data` 被重建
2. 缺乏操作前的備份驗證
3. 缺乏操作審計和風險評估
4. AI Agent 或執行者無法獲取操作規範
5. 缺乏即時的異常監控告警

### 治理框架缺口

| 層面 | 現狀 | 問題 |
|------|------|------|
| **防護層面** | ❌ 空白 | API 層面無危險操作保護，缺乏多級審批 |
| **監控層面** | ⚠️ 部分 | 有日志但無實時監控告警，缺乏異常檢測 |
| **Agent 治理** | ❌ 空白 | AI Agent 無操作規範知識庫，無風險評估機制 |
| **合規層面** | ⚠️ 計劃 | 有 ISO/IEC 42001 合規計劃但未實施 |
| **恢復層面** | ✅ 基礎 | 有備份規範但未設置定時任務 |

---

## AI 治理框架設計

### 整體架構

```
┌─────────────────────────────────────────────────────────┐
│                  AI-Box AI 治理層次                   │
├─────────────────────────────────────────────────────────┤
│  Layer 5: 恢復層面 (Recovery Layer)                  │
│  - 數據恢復腳本                                        │
│  - 定期恢復測試                                      │
│  - 災難回應流程                                        │
├─────────────────────────────────────────────────────────┤
│  Layer 4: 合規層面 (Compliance Layer)                │
│  - ISO/IEC 42001 合規檢查                              │
│  - AIGP/AAIA/AAISM 合規檢查                           │
│  - 數據分類與標記                                      │
│  - 合規報告生成                                        │
├─────────────────────────────────────────────────────────┤
│  Layer 3: Agent 治理 (Agent Governance)                │
│  - 治理知識庫注入                                      │
│  - AI Agent 風險評估                                    │
│  - 自動備份協議                                        │
│  - 操作權限控制                                        │
├─────────────────────────────────────────────────────────┤
│  Layer 2: 監控層面 (Monitoring Layer)                  │
│  - 實時數據量監控                                      │
│  - 異常檢測告警                                        │
│  - 備份狀態監控                                        │
│  - 風險閾值告警                                        │
└─────────────────────────────────────────────────────────┘
│  Layer 1: 防護層面 (Protection Layer)                  │
│  - API 層危險操作攔截                                    │
│  - 數據修改前置備份                                    │
│  - 多級審批機制                                        │
│  - 操作審計日誌                                        │
└─────────────────────────────────────────────────────────┘
```

---

## Layer 1: 防護層面

### 1.1 API 層危險操作保護

**目標**: 在 API 層面攔截並控制危險操作

**實施方案**:

```python
# 位置: api/middleware/operation_guard.py

class OperationGuardMiddleware:
    """操作守衛中間件"""
    
    # 危險操作白名單（需要審批）
    DANGEROUS_OPERATIONS = {
        "DROP_DATABASE",
        "TRUNCATE_COLLECTION",
        "DELETE_ALL_DOCUMENTS",
        "DROP_COLLECTION",
    }
    
    # 限制操作速率
    RATE_LIMITS = {
        "DROP_DATABASE": {"count": 1, "period": 3600},  # 每小時最多 1 次
        "TRUNCATE_COLLECTION": {"count": 3, "period": 3600},
    }
    
    async def __call__(self, request: Request, call_next):
        operation = self._extract_operation(request)
        
        if operation in self.DANGEROUS_OPERATIONS:
            # 檢查速率限制
            if not await self._check_rate_limit(operation):
                raise HTTPException(403, "操作頻率超限")
            
            # 強制備份
            backup_status = await self._verify_recent_backup()
            if not backup_status:
                raise HTTPException(400, "無最近備份，請先備份")
            
            # 多級審批
            approval = await self._get_approval(operation, request)
            if not approval:
                raise HTTPException(403, "等待審批")
            
            # 記錄審計
            await self._audit_log(request, operation, approval)
        
        return await call_next(request)
```

**實施步驟**:
1. [ ] 創建 `api/middleware/operation_guard.py`
2. [ ] 註冊中間件到 FastAPI
3. [ ] 定義危險操作清單
4. [ ] 實現操作速率限制
5. [ ] 集成備份驗證
6. [ ] 實現多級審批機制（待用戶系統完成）
7. [ ] 集成審計日誌

**預期效果**:
- 阻止未備份的危險操作
- 控制危險操作頻率
- 保留完整審計追蹤

### 1.2 數據修改前置備份

**目標**: 重大修改前強制備份

**實施方案**:

```python
# 位置: services/api/services/pre_operation_backup.py

class PreOperationBackupService:
    """操作前備份服務"""
    
    async def backup_before_operation(
        self,
        operation: str,
        service: str,  # arangodb, qdrant, seaweedfs
        force: bool = False,
    ) -> str:
        """操作前備份
        
        Returns:
            備份 ID
        """
        # 檢查是否需要備份
        if not self._requires_backup(operation) and not force:
            return None
        
        # 標記備份用途
        backup_label = f"pre_{operation}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # 執行快速備份（僅備份修改的部分）
        if service == "arangodb":
            backup_id = await self._backup_arangodb_fast(backup_label)
        elif service == "qdrant":
            backup_id = await self._backup_qdrant_fast(backup_label)
        # ...
        
        # 記錄備份關聯
        await self._link_backup_to_operation(backup_id, operation)
        
        return backup_id
```

**實施步驟**:
1. [ ] 創建 `services/api/services/pre_operation_backup.py`
2. [ ] 實現快速備份邏輯（增量備份）
3. [ ] 實現備份用途標記
4. [ ] 集成到所有數據修改 API
5. [ ] 實現備份關聯查詢

**預期效果**:
- 重大修改前自動備份
- 可追溯每個操作的備份
- 支援快速回滾

### 1.3 多級審批機制

**目標**: 危險操作需要多人審批

**審批級別**:

| 級別 | 操作類型 | 審批要求 |
|------|---------|---------|
| Level 1 | 一般數據修改 | 無需審批 |
| Level 2 | 批量刪除 | 1 人審批 |
| Level 3 | 清空 Collection | 2 人審批 |
| Level 4 | DROP DATABASE | 3 人審批 + 系統管理員 |
| Level 5 | 數據卷重建 | 需要變更管理委員會批准 |

**實施步驟**:
1. [ ] 創建 `services/api/services/approval_service.py`
2. [ ] 定義審批工作流
3. [ ] 實現審批請求 API
4. [ ] 實現審批決策 API
5. [ ] 集成到操作守衛中間件
6. [ ] 實現審批狀態查詢

### 1.4 操作審計日誌增強

**目標**: 詳細記錄所有操作

**實施方案**:

```python
# 位置: services/api/services/enhanced_audit_log_service.py

class EnhancedAuditLogService:
    """增強審計日誌服務"""
    
    async def log_operation(
        self,
        user_id: str,
        operation_type: str,
        resource_type: str,
        resource_id: str,
        context: dict,  # 額外上下文信息
        risk_level: str,  # low/medium/high/critical
        approval_id: Optional[str],  # 審批 ID（如果需要）
    ):
        """記錄操作審計"""
        
        # 計算風險分數
        risk_score = self._calculate_risk_score(operation_type, context)
        
        # 自動分類
        classification = self._classify_operation(operation_type)
        
        # 記錄到審計日誌
        await self._record_audit({
            "timestamp": datetime.utcnow(),
            "user_id": user_id,
            "operation_type": operation_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "context": context,
            "risk_level": risk_level,
            "risk_score": risk_score,
            "classification": classification,
            "approval_id": approval_id,
            "ip_address": self._get_ip_address(),
            "user_agent": self._get_user_agent(),
        })
        
        # 高風險操作立即告警
        if risk_level in ["high", "critical"]:
            await self._send_alert({
                "type": "high_risk_operation",
                "operation": operation_type,
                "user_id": user_id,
                "context": context,
            })
```

**實施步驟**:
1. [ ] 創建 `services/api/services/enhanced_audit_log_service.py`
2. [ ] 實現風險評分算法
3. [ ] 實現操作分類
4. [ ] 集成到所有數據操作 API
5. [ ] 實現高風險告警
6. [ ] 提供審計查詢 API

---

## Layer 2: 監控層面

### 2.1 實時數據量監控

**目標**: 檢測數據量異常變化

**監控指標**:

| 指標 | 正常範圍 | 警告閾值 | 危險閾值 |
|------|---------|---------|---------|
| ArangoDB 文檔數 | ±5% / 小時 | ±20% / 小時 | 突變 -50% 以上 |
| Qdrant 向量數 | ±5% / 小時 | ±20% / 小時 | 突變 -50% 以上 |
| SeaWeedFS 文件數 | ±10% / 天 | ±30% / 天 | 突變 -70% 以上 |
| 數據卷大小 | 平穩增長 | 下降 > 10% | 下降 > 50% |

**實施方案**:

```python
# 位置: services/api/services/data_volume_monitor.py

class DataVolumeMonitor:
    """數據量監控服務"""
    
    async def check_volume_changes(self):
        """檢查數據量變化"""
        
        # 獲取當前數據量
        current_stats = {
            "arangodb": await self._get_arangodb_stats(),
            "qdrant": await self._get_qdrant_stats(),
            "seaweedfs": await self._get_seaweedfs_stats(),
        }
        
        # 與前一次比較
        previous_stats = await self._get_previous_stats()
        
        # 計算變化率
        changes = self._calculate_changes(current_stats, previous_stats)
        
        # 檢查異常
        anomalies = self._detect_anomalies(changes)
        
        # 記錄監控數據
        await self._record_monitoring_stats(current_stats, changes)
        
        # 發送告警
        for anomaly in anomalies:
            await self._send_alert(anomaly)
        
        return changes
```

**實施步驟**:
1. [ ] 創建 `services/api/services/data_volume_monitor.py`
2. [ ] 實現數據量統計
3. [ ] 實現變化率計算
4. [ ] 實現異常檢測算法
5. [ ] 實現告警機制
6. [ ] 設置定時監控任務（每 10 分鐘）

### 2.2 異常檢測告警

**目標**: 檢測並告警異常操作

**檢測類型**:

1. **數據丟失檢測**
   - 文檔數突然下降
   - Collection 被清空
   - 數據卷被重建

2. **異常操作模式檢測**
   - 短時間內大量刪除
   - 非工作時間的批量操作
   - 管理員權限的異常使用

3. **數據完整性檢測**
   - 索引缺失
   - 外鍵約束違規
   - 數據格式異常

**實施步驟**:
1. [ ] 創建 `services/api/services/anomaly_detection_service.py`
2. [ ] 實現統計異常檢測（基於 3σ 規則）
3. [ ] 實現模式識別（基於機器學習）
4. [ ] 實現實時告警
5. [ ] 集成到監控服務

### 2.3 備份狀態監控

**目標**: 確保備份正常運行

**監控項目**:

| 項目 | 頻率 | 成功標準 |
|------|------|---------|
| 備份執行 | 每次 | 成功率 > 95% |
| 備份完成時間 | 每次 | < 10 分鐘 |
| 備份文件完整性 | 每天 | 可解壓驗證通過 |
| 備份存儲空間 | 每天 | < 50GB |
| 最近備份時間 | 每天 | < 2 小時前 |

**實施方案**:

```python
# 位置: services/api/services/backup_monitor.py

class BackupMonitor:
    """備份監控服務"""
    
    async def check_backup_status(self):
        """檢查備份狀態"""
        
        # 獲取最近的備份
        recent_backups = await self._get_recent_backups(hours=2)
        
        if not recent_backups:
            await self._send_alert({
                "type": "backup_missing",
                "severity": "critical",
                "message": "最近 2 小時內無備份",
            })
            return False
        
        # 檢查備份文件完整性
        for backup in recent_backups:
            is_valid = await self._verify_backup_integrity(backup)
            if not is_valid:
                await self._send_alert({
                    "type": "backup_corrupted",
                    "severity": "critical",
                    "backup_id": backup["id"],
                })
        
        # 檢查存儲空間
        storage_usage = await self._check_storage_usage()
        if storage_usage > 0.8:  # 80%
            await self._send_alert({
                "type": "storage_high",
                "severity": "warning",
                "usage": f"{storage_usage*100:.1f}%",
            })
        
        return True
```

**實施步驟**:
1. [ ] 創建 `scripts/backup_monitor.py`（已存在，需增強）
2. [ ] 實現備份完整性驗證
3. [ ] 實現存儲空間檢查
4. [ ] 實現告警機制
5. [ ] 設置定時監控（每 15 分鐘）

### 2.4 風險閾值告警

**目標**: 基於風險閾值觸發告警

**風險閾值配置**:

```yaml
# 位置: config/governance_risk_thresholds.yml

risk_thresholds:
  data_loss:
    document_drop_rate: 0.5  # 文檔下降 50%
    collection_truncated: true  # Collection 被清空
    volume_rebuilt: true  # 數據卷被重建
    severity: critical
  
  abnormal_operations:
    delete_rate_per_minute: 100  # 每分鐘刪除 100 個
    non_admin_bulk_operation: true  # 非管理員批量操作
    night_time_operation: true  # 非工作時間操作
    severity: high
  
  backup:
    missing_hours: 2  # 缺少 2 小時備份
    failure_rate: 0.05  # 失敗率 > 5%
    corrupted_backup: true  # 備份文件損壞
    severity: warning
  
  storage:
    usage_threshold: 0.8  # 使用率 > 80%
    low_space_gb: 10  # 剩餘空間 < 10GB
    severity: warning
```

**實施步驟**:
1. [ ] 創建 `config/governance_risk_thresholds.yml`
2. [ ] 創建 `services/api/services/risk_threshold_service.py`
3. [ ] 實現閾值檢查邏輯
4. [ ] 實現分級告警（critical/high/warning/info）
5. [ ] 集成到監控服務

---

## Layer 3: Agent 治理

### 3.1 治理知識庫注入

**目標**: 讓 AI Agent 理解並遵守操作規範

**治理知識庫結構**:

```json
{
  "knowledge_base": {
    "name": "AI-Box 操作規範知識庫",
    "version": "1.0",
    "domains": [
      {
        "domain": "數據操作規範",
        "rules": [
          {
            "rule_id": "DATA_OP_001",
            "title": "禁止未備份刪除數據",
            "description": "刪除或修改數據前必須先備份",
            "exceptions": ["臨時數據（TTL collection）"],
            "severity": "critical",
            "action_required": "pre_backup",
            "evidence_required": ["backup_id"],
            "example": {
              "violation": "刪除 ontologies collection 中的所有文檔",
              "correct": "先執行備份，然後再刪除"
            }
          },
          {
            "rule_id": "DATA_OP_002",
            "title": "禁止重建數據卷",
            "description": "重建數據卷會丟失所有數據，必須有明確批准和備份",
            "exceptions": [],
            "severity": "critical",
            "action_required": ["multi_level_approval", "verified_backup"],
            "evidence_required": ["backup_id", "approval_ids"],
            "example": {
              "violation": "執行 docker volume rm ai-box_arangodb_data",
              "correct": "獲得多級審批，執行完整備份，然後重建"
            }
          },
          {
            "rule_id": "DATA_OP_003",
            "title": "重大變更前備份",
            "description": "Schema 變更、結構調整等重大變更前必須備份",
            "exceptions": [],
            "severity": "high",
            "action_required": "pre_backup",
            "evidence_required": ["backup_id"],
            "example": {
              "violation": "修改 ArangoDB schema，添加新 collection",
              "correct": "先備份當前 schema 和數據，然後修改"
            }
          },
          {
            "rule_id": "DATA_OP_004",
            "title": "記錄所有數據操作",
            "description": "所有數據修改操作必須記錄到審計日誌",
            "exceptions": ["查詢操作"],
            "severity": "medium",
            "action_required": "audit_logging",
            "evidence_required": ["operation_id"],
            "example": {
              "violation": "修改 config without logging",
              "correct": "調用 audit_log_service 記錄操作"
            }
          }
        ]
      },
      {
        "domain": "備份與恢復規範",
        "rules": [
          {
            "rule_id": "BACKUP_001",
            "title": "定期備份執行",
            "description": "系統每小時自動執行備份，保留 7 天",
            "severity": "high",
            "action_required": "scheduled_backup",
            "monitoring": "check_backup_status"
          },
          {
            "rule_id": "BACKUP_002",
            "title": "恢復前驗證",
            "description": "恢復數據前必須驗證備份文件完整性和可用性",
            "severity": "high",
            "action_required": "backup_verification",
            "evidence_required": ["backup_verification_result"]
          },
          {
            "rule_id": "BACKUP_003",
            "title": "恢復後驗證",
            "description": "恢復後必須驗證數據完整性和功能正常",
            "severity": "high",
            "action_required": "post_restore_verification",
            "evidence_required": ["verification_report"]
          }
        ]
      },
      {
        "domain": "風險評估規範",
        "rules": [
          {
            "rule_id": "RISK_001",
            "title": "操作前風險評估",
            "description": "執行任何數據修改操作前必須評估風險",
            "severity": "high",
            "action_required": "risk_assessment",
            "risk_levels": {
              "low": "查詢操作、單個文檔修改",
              "medium": "批量修改、Schema 輕微調整",
              "high": "清空 Collection、大量刪除",
              "critical": "DROP DATABASE、重建數據卷"
            },
            "mitigation_strategies": {
              "low": "無需特殊措施",
              "medium": "備份 + 審計日誌",
              "high": "備份 + 多級審批 + 審計日誌",
              "critical": "完整備份 + 多級審批 + 審計日誌 + 變更管理委員會批准"
            }
          },
          {
            "rule_id": "RISK_002",
            "title": "AI Agent 風險感知",
            "description": "AI Agent 必須能識別操作風險並採取相應措施",
            "severity": "high",
            "action_required": "agent_risk_awareness",
            "agent_capabilities": {
              "risk_identification": "識別操作風險等級",
              "mitigation_suggestion": "建議風險緩解措施",
              "evidence_collection": "收集必要的證據（備份 ID、審批 ID）",
              "escalation": "高風險操作自動升級到人工審批"
            }
          }
        ]
      }
    ]
  }
}
```

**知識庫注入機制**:

```python
# 位置: agents/governance/governance_knowledge_base.py

class GovernanceKnowledgeBase:
    """治理知識庫服務"""
    
    def __init__(self):
        self.knowledge_base_path = Path("kag/ontology/governance_knowledge.json")
        self.rules = self._load_knowledge_base()
    
    async def get_relevant_rules(
        self,
        operation_type: str,
        context: dict,
    ) -> list[dict]:
        """獲取相關規則"""
        
        # 根據操作類型和上下文篩選規則
        relevant_rules = []
        for rule in self.rules["knowledge_base"]["domains"]:
            if self._is_relevant(rule, operation_type, context):
                relevant_rules.append(rule)
        
        # 按嚴重程度排序
        relevant_rules.sort(key=lambda x: self._get_severity_order(x["severity"]))
        
        return relevant_rules
    
    async def check_compliance(
        self,
        operation: dict,
        evidence: dict,
    ) -> dict:
        """檢查操作是否合規"""
        
        # 獲取相關規則
        rules = await self.get_relevant_rules(
            operation["type"],
            operation.get("context", {}),
        )
        
        # 檢查每條規則
        compliance_result = {
            "compliant": True,
            "violations": [],
            "required_actions": [],
            "evidence_needed": [],
        }
        
        for rule in rules:
            if not self._check_rule_compliance(operation, rule, evidence):
                compliance_result["compliant"] = False
                compliance_result["violations"].append({
                    "rule_id": rule["rule_id"],
                    "title": rule["title"],
                    "severity": rule["severity"],
                })
                
                if rule.get("action_required"):
                    compliance_result["required_actions"].append(
                        rule["action_required"]
                    )
                
                if rule.get("evidence_required"):
                    compliance_result["evidence_needed"].extend(
                        rule["evidence_required"]
                    )
        
        return compliance_result
```

**實施步驟**:
1. [ ] 創建 `kag/ontology/governance_knowledge.json`
2. [ ] 創建 `agents/governance/governance_knowledge_base.py`
3. [ ] 定義完整的操作規範
4. [ ] 實現規則檢索邏輯
5. [ ] 實現合規檢查邏輯
6. [ ] 集成到所有 AI Agent

### 3.2 AI Agent 風險評估

**目標**: AI Agent 執行操作前自動評估風險

**風險評估流程**:

```python
# 位置: agents/governance/risk_assessment_agent.py

class RiskAssessmentAgent:
    """風險評估 Agent"""
    
    async def assess_operation_risk(
        self,
        operation: dict,
        user_context: dict,
    ) -> dict:
        """評估操作風險"""
        
        # 1. 獲取相關規則
        governance_kb = GovernanceKnowledgeBase()
        rules = await governance_kb.get_relevant_rules(
            operation["type"],
            operation.get("context", {}),
        )
        
        # 2. 分析操作上下文
        context_analysis = self._analyze_context(operation, user_context)
        
        # 3. 計算風險分數
        risk_score = self._calculate_risk_score(
            operation,
            context_analysis,
            rules,
        )
        
        # 4. 確定風險等級
        risk_level = self._determine_risk_level(risk_score)
        
        # 5. 建議緩解措施
        mitigation = self._suggest_mitigation(
            operation,
            risk_level,
            rules,
        )
        
        return {
            "operation": operation,
            "risk_score": risk_score,
            "risk_level": risk_level,
            "context_analysis": context_analysis,
            "relevant_rules": [r["rule_id"] for r in rules],
            "mitigation": mitigation,
            "can_proceed": risk_level != "critical",
            "requires_approval": risk_level in ["high", "critical"],
            "required_evidence": self._get_required_evidence(operation, rules),
        }
```

**風險評估模型**:

```python
def _calculate_risk_score(
    self,
    operation: dict,
    context: dict,
    rules: list[dict],
) -> float:
    """計算風險分數"""
    
    base_score = 0
    
    # 規則影響
    for rule in rules:
        severity_weight = {
            "low": 10,
            "medium": 30,
            "high": 70,
            "critical": 100,
        }
        base_score += severity_weight.get(rule["severity"], 0)
    
    # 上下文影響
    context_factors = {
        "is_admin": context.get("is_admin", False),
        "is_business_hours": self._is_business_hours(),
        "has_recent_backup": context.get("has_recent_backup", False),
        "operation_frequency": context.get("recent_operation_count", 0),
    }
    
    if not context_factors["is_admin"]:
        base_score += 20
    
    if not context_factors["is_business_hours"]:
        base_score += 15
    
    if not context_factors["has_recent_backup"]:
        base_score += 30
    
    if context_factors["operation_frequency"] > 10:
        base_score += 25
    
    # 歸一化到 0-100
    return min(base_score, 100)
```

**實施步驟**:
1. [ ] 創建 `agents/governance/risk_assessment_agent.py`
2. [ ] 實現風險評估模型
3. [ ] 集成治理知識庫
4. [ ] 實現上下文分析
5. [ ] 實現緩解措施建議
6. [ ] 集成到所有 AI Agent

### 3.3 自動備份協議

**目標**: AI Agent 執行操作前自動檢查並執行備份

**備份協議流程**:

```python
# 位置: agents/governance/backup_protocol_agent.py

class BackupProtocolAgent:
    """備份協議 Agent"""
    
    async def ensure_backup_before_operation(
        self,
        operation: dict,
    ) -> dict:
        """確保操作前有備份"""
        
        # 1. 檢查最近的備份
        backup_service = BackupService()
        recent_backup = await backup_service.get_recent_backup(
            service=operation.get("service"),
            hours=1,
        )
        
        # 2. 如果有備份，記錄備份 ID
        if recent_backup:
            return {
                "backup_id": recent_backup["id"],
                "backup_time": recent_backup["timestamp"],
                "status": "ready_to_proceed",
                "message": "使用最近備份",
            }
        
        # 3. 如果無備份，執行快速備份
        logger.warning(
            "no_recent_backup_found",
            operation=operation["type"],
            service=operation.get("service"),
        )
        
        backup_id = await backup_service.create_quick_backup(
            service=operation.get("service"),
            label=f"pre_{operation['type']}",
        )
        
        return {
            "backup_id": backup_id,
            "backup_time": datetime.utcnow().isoformat(),
            "status": "backup_created",
            "message": "已創建操作前備份",
        }
```

**實施步驟**:
1. [ ] 創建 `agents/governance/backup_protocol_agent.py`
2. [ ] 實現快速備份邏輯
3. [ ] 集成到風險評估 Agent
4. [ ] 實現備份狀態檢查
5. [ ] 實現備份失敗處理

### 3.4 操作權限控制

**目標**: 控制 AI Agent 的數據操作權限

**權限級別**:

| 級別 | 權限 | 允許的操作 |
|------|------|-----------|
| Read-Only | 僅讀取 | 查詢、統計 |
| Limited-Write | 限制寫入 | 單個文檔修改、新增 |
| Bulk-Write | 批量寫入 | 批量新增、部分刪除 |
| Full-Write | 完全寫入 | 所有修改、清空 Collection |
| Admin | 管理員 | DROP DATABASE、重建數據卷 |

**權限檢查機制**:

```python
# 位置: agents/governance/permission_control_agent.py

class PermissionControlAgent:
    """權限控制 Agent"""
    
    async def check_permission(
        self,
        agent_id: str,
        operation: dict,
    ) -> dict:
        """檢查 Agent 權限"""
        
        # 1. 獲取 Agent 權限級別
        agent_permission = await self._get_agent_permission(agent_id)
        
        # 2. 獲取操作所需權限
        required_permission = self._get_required_permission(operation)
        
        # 3. 檢查權限
        if self._has_permission(agent_permission, required_permission):
            return {
                "allowed": True,
                "permission": agent_permission,
                "message": "權限足夠",
            }
        
        # 4. 權限不足，需要升級
        return {
            "allowed": False,
            "current_permission": agent_permission,
            "required_permission": required_permission,
            "message": "權限不足，需要人工審批",
            "escalation_required": True,
        }
```

**實施步驟**:
1. [ ] 創建 `agents/governance/permission_control_agent.py`
2. [ ] 定義權限級別和映射
3. [ ] 實現權限檢查邏輯
4. [ ] 實現權限升級流程
5. [ ] 集成到所有 AI Agent

---

## Layer 4: 合規層面

### 4.1 數據分類與標記

**目標**: 實現數據分類和敏感性標記

**分類標準**:

```python
# 位置: services/api/models/data_classification.py

class DataClassification:
    """數據分類標準"""
    
    PUBLIC = "PUBLIC"  # 公開數據
    INTERNAL = "INTERNAL"  # 內部數據
    CONFIDENTIAL = "CONFIDENTIAL"  # 機密數據
    RESTRICTED = "RESTRICTED"  # 限制訪問數據
```

**敏感性標籤**:

```python
class SensitivityLabel:
    """敏感性標籤"""
    
    PII = "PII"  # 個人信息
    PHI = "PHI"  # 醫療信息
    FINANCIAL = "FINANCIAL"  # 財務信息
    IP = "IP"  # 知識產權
    CUSTOMER = "CUSTOMER"  # 客戶數據
    PROPRIETARY = "PROPRIETARY"  # 專有數據
```

**實施步驟**:
1. [ ] 更新數據模型添加分類字段
2. [ ] 實現自動分類邏輯（基於內容和上下文）
3. [ ] 實現人工分類 API
4. [ ] 集成分類到數據服務
5. [ ] 實現基於分類的訪問控制

### 4.2 自動化合規檢查

**目標**: 實現 ISO/IEC 42001 合規檢查

**檢查項目**:

| 類別 | 檢查項目 | 頻率 |
|------|---------|------|
| 數據治理 | 數據分類正確性 | 每週 |
| 數據治理 | 數據保留政策 | 每月 |
| 數據治理 | 數據品質 | 每週 |
| 數據治理 | 數據完整性 | 每天 |
| 數據安全 | 加密要求 | 每月 |
| 數據安全 | 訪問控制 | 每週 |
| 數據安全 | 審計日誌完整性 | 每天 |
| 數據隱私 | PII 保護 | 每週 |

**實施步驟**:
1. [ ] 創建 `services/api/services/compliance_check_service.py`
2. [ ] 實現 ISO/IEC 42001 檢查清單
3. [ ] 實現自動化檢查邏輯
4. [ ] 實現檢查報告生成
5. [ ] 實現檢查結果追蹤

### 4.3 合規報告生成

**目標**: 自動生成合規報告

**報告類型**:

1. **日報**: 數據操作摘要、安全事件
2. **週報**: 合規檢查結果、風險趨勢
3. **月報**: 全面合規狀態、改進計劃
4. **事件報告**: 異常事件詳情、處理過程

**實施步驟**:
1. [ ] 創建 `services/api/services/compliance_report_service.py`
2. [ ] 設計報告模板
3. [ ] 實現數據聚合邏輯
4. [ ] 實現報告生成 API
5. [ ] 實現定時報告生成

---

## Layer 5: 恢復層面

### 5.1 數據恢復腳本

**目標**: 提供統一、安全的恢復工具

**狀態**: ✅ 已完成（`scripts/restore_all.py`）

**功能**:
- 支援恢復所有 4 個服務
- 互動式選擇備份
- 自動確認提示
- 完整的錯誤處理

### 5.2 定期恢復測試

**目標**: 驗證備份可用性

**測試計劃**:

| 頻率 | 測試內容 |
|------|---------|
| 每天 | 驗證最新備份可解壓 |
| 每週 | 恢復測試環境並驗證 |
| 每月 | 完整恢復演練 |
| 事件後 | 立即恢復測試 |

**實施方案**:

```python
# 位置: services/api/services/restore_test_service.py

class RestoreTestService:
    """恢復測試服務"""
    
    async def test_restore(
        self,
        backup_file: Path,
        service: str,
    ) -> dict:
        """測試恢復可用性"""
        
        # 1. 驗證備份文件完整性
        is_valid = await self._verify_backup_integrity(backup_file)
        if not is_valid:
            return {
                "success": False,
                "error": "backup_file_corrupted",
            }
        
        # 2. 恢復到測試環境
        test_result = await self._restore_to_test_environment(
            backup_file,
            service,
        )
        
        # 3. 驗證數據
        verification = await self._verify_restored_data(
            service,
        )
        
        return {
            "success": test_result["success"] and verification["success"],
            "backup_file": str(backup_file),
            "service": service,
            "verification": verification,
            "timestamp": datetime.utcnow().isoformat(),
        }
```

**實施步驟**:
1. [ ] 創建測試環境配置
2. [ ] 實現恢復測試服務
3. [ ] 實現數據驗證邏輯
4. [ ] 設置定時測試任務
5. [ ] 實現測試結果報告

### 5.3 災難回應流程

**目標**: 標準化數據丟失處理流程

**流程圖**:

```
數據丟失事件發生
    ↓
立即停止所有數據修改操作
    ↓
確認丟失範圍和時間
    ↓
選擇恢復策略：
    ├─ 從備份恢復（推薦）
    ├─ 從日誌重建（部分恢復）
    └─ 通知用戶（完全丟失）
    ↓
執行恢復
    ↓
驗證恢復結果
    ↓
事故回顧和改進
```

**實施步驟**:
1. [ ] 創建 `docs/系統管理/災難回應流程.md`
2. [ ] 創建 `scripts/disaster_response.sh`
3. [ ] 實現自動化回應工具
4. [ ] 訓練應急響應團隊

---

## 實施路線圖

### Phase 1: 緊急防護（優先級：P0）

**目標**: 立即阻止數據丟失事件重演

**工期**: 3 天

| 任務 | 依賴 | 負任人 | 狀態 |
|------|------|--------|------|
| API 層危險操作保護 | � | 後端 | |
| 操作審計日誌增強 | 無 | 後端 | |
| 備份狀態監控 | 無 | 後端 | |
| 數據量監控 | 無 | 後端 | |
| 定時備份任務設置 | 無 | 運維 | |

### Phase 2: 監控強化（優先級：P1）

**目標**: 建立完善的監控告警系統

**工期**: 5 天

| 任務 | 依賴 | 負任人 | 狀態 |
|------|------|--------|------|
| 異常檢測告警 | Phase 1 | 後端 | |
| 風險閾值告警 | Phase 1 | 後端 | |
| 治理儀表板 | Phase 1 | 前端 | |
| 告警通知系統 | Phase 1 | 後端 | |
| 監控數據存儲 | Phase 1 | 後端 | |

### Phase 3: Agent 治理（優先級：P1）

**目標**: AI Agent 自動遵守操作規範

**工期**: 7 天

| 任務 | 依賴 | 負任人 | 狀態 |
|------|------|--------|------|
| 治理知識庫注入 | 無 | AI 團隊 | |
| 風險評估 Agent | 無 | AI 團隊 | |
| 自動備份協議 | 無 | AI 團隊 | |
| 權限控制 Agent | 無 | AI 團隊 | |
| Agent 治理測試 | 以上所有 | 測試 | |

### Phase 4: 合規實施（優先級：P2）

**目標**: 實現合規標準要求

**工期**: 10 天

| 任務 | 依賴 | 負任人 | 狀態 |
|------|------|--------|------|
| 數據分類與標記 | Phase 1 | 後端 | |
| 合規檢查服務 | Phase 2 | 後端 | |
| 合規報告生成 | Phase 2 | 後端 | |
| 合規儀表板 | Phase 2 | 前端 | |
| 外部審計準備 | 以上所有 | 合規 | |

### Phase 5: 恢復優化（優先級：P2）

**目標**: 提升恢復效率和可靠性

**工期**: 7 天

| 任務 | 依賴 | 負任人 | 狀態 |
|------|------|--------|------|
| 恢復腳本優化 | 無 | 運維 | |
| 恢復測試服務 | 無 | 測試 | |
| 災難回應流程 | 無 | 運維 | |
| 回應演練 | Phase 4 | 運維 | |
| 文檔完善 | 所有 | 文檔 | |

---

## 預期效果

### 風險降低

| 風險類型 | 實施前 | 實施後 | 降低幅度 |
|---------|--------|--------|---------|
| 數據丟失 | 高 | 低 | 90% |
| 未備份操作 | 高 | 零 | 95% |
| 異常操作 | 中 | 低 | 80% |
| 合規違規 | 高 | 低 | 85% |

### 合規性提升

| 標準 | 實施前 | 實施後 | 提升幅度 |
|------|--------|--------|---------|
| ISO/IEC 42001 | 20% | 90% | 70% |
| AIGP | 30% | 85% | 55% |
| AAIA | 25% | 80% | 55% |
| AAISM | 20% | 75% | 55% |

### 運營效率

| 指標 | 實施前 | 實施後 | 提升幅度 |
|------|--------|--------|---------|
| 平均恢復時間 | 4 小時 | 30 分鐘 | 87.5% |
| 合規報告生成 | 8 小時 | 自動 | 100% |
| 監控覆蓋率 | 40% | 95% | 55% |

---

## 文檔維護

### 版本記錄

| 版本 | 日期 | 修改人員 | 修改內容 |
|------|------|---------|---------|
| 1.0 | 2026-01-27 | Daniel Chung | 初始版本，基於 2026-01-25 數據丟失事件制定 |

### 相關文檔

- [數據備份規範](數據備份規範.md)
- [WBS-4: AI 治理與合規](../../../備份與歸檔/文件管理歸檔/migration/WBS-4-AI治理與合規.md)
- [WBS-階段六：AI 治理](../../../開發過程文檔/plans/rag-file-upload/wbs-phase6-ai-governance.md)
- [備份腳本](../../../../scripts/backup_all.py)
- [恢復腳本](../../../../scripts/restore_all.py)

---

## 審查清單

在實施前，請確認以下事項：

- [ ] 這份規劃已經過技術審查
- [ ] 這份規劃已經過安全審查
- [ ] 這份規劃已經過合規審查
- [ ] 所有依賴的技術棧已確認
- [ ] 實施團隊已組建
- [ ] 實施資源已分配
- [ ] 實施時間表已確認
- [ ] 回滾計劃已準備

---

## 行動項

請在審查後確定以下行動項：

- [ ] 批准這份規劃
- [ ] 確認實施優先級
- [ ] 分配實施資源
- [ ] 設置實施時間表
- [ ] 指派項目經理
- [ ] 建立審查流程
