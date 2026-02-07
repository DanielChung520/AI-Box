# 🧩 Agent Todo 作業 規範（chatGPT 建議版）

## 1️⃣ 設計原則（先立法）

**Todo 不是任務描述，而是「可觀測、可驗證的執行單位」**

核心原則只有四條：

1. **狀態外部化** （Agent 無權私藏狀態）
2. **前後條件明確化** （不是自由發揮）
3. **失敗是結構化輸出** （不是例外）
4. **結果必須可被消費** （machine-readable）

---

## 2️⃣ Todo Schema（正式結構）

### 🔹 2.1 基本結構（Minimal Viable）

<pre class="overflow-visible! px-0!" data-start="500" data-end="997"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(var(--sticky-padding-top)+9*var(--spacing))]"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"todo_id"</span><span>:</span><span></span><span>"TODO-20260207-00031"</span><span>,</span><span>
  </span><span>"type"</span><span>:</span><span></span><span>"DATA_QUERY"</span><span>,</span><span>
  </span><span>"domain"</span><span>:</span><span></span><span>"ERP.PURCHASE"</span><span>,</span><span>
  </span><span>"priority"</span><span>:</span><span></span><span>"NORMAL"</span><span>,</span><span>

  </span><span>"owner_agent"</span><span>:</span><span></span><span>"DA"</span><span>,</span><span>
  </span><span>"dispatcher"</span><span>:</span><span></span><span>"BPA"</span><span>,</span><span>

  </span><span>"input"</span><span>:</span><span></span><span>{</span><span>}</span><span>,</span><span>
  </span><span>"context_refs"</span><span>:</span><span></span><span>[</span><span>]</span><span>,</span><span>
  </span><span>"constraints"</span><span>:</span><span></span><span>{</span><span>}</span><span>,</span><span>

  </span><span>"state"</span><span>:</span><span></span><span>"PENDING"</span><span>,</span><span>
  </span><span>"retry"</span><span>:</span><span></span><span>{</span><span>
    </span><span>"max"</span><span>:</span><span></span><span>3</span><span>,</span><span>
    </span><span>"policy"</span><span>:</span><span></span><span>"EXPONENTIAL_BACKOFF"</span><span>
  </span><span>}</span><span>,</span><span>

  </span><span>"preconditions"</span><span>:</span><span></span><span>[</span><span>]</span><span>,</span><span>
  </span><span>"postconditions"</span><span>:</span><span></span><span>[</span><span>]</span><span>,</span><span>

  </span><span>"artifacts"</span><span>:</span><span></span><span>[</span><span>]</span><span>,</span><span>
  </span><span>"error"</span><span>:</span><span></span><span>null</span><span></span><span>,</span><span>

  </span><span>"timestamps"</span><span>:</span><span></span><span>{</span><span>
    </span><span>"created_at"</span><span>:</span><span></span><span>"2026-02-07T04:30:00Z"</span><span>,</span><span>
    </span><span>"updated_at"</span><span>:</span><span></span><span>null</span><span>
  </span><span>}</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

---

### 🔹 2.2 欄位語意定義（重點）

#### ▪️ type（任務類型，正面表列）

<pre class="overflow-visible! px-0!" data-start="1051" data-end="1173"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(var(--sticky-padding-top)+9*var(--spacing))]"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-text"><span><span>DATA_QUERY
DATA_WRITE
SCHEMA_VALIDATE
TRANSFORM
ANALYSIS
DECISION
NOTIFICATION
MEMORY_UPDATE
HUMAN_INTERACTION
</span></span></code></div></div></pre>

> ⚠️ Agent **不得自行發明 type**

---

#### ▪️ domain（業務語意錨點）

<pre class="overflow-visible! px-0!" data-start="1231" data-end="1314"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(var(--sticky-padding-top)+9*var(--spacing))]"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-text"><span><span>ERP.PURCHASE
ERP.INVENTORY
MES.PRODUCTION
FIN.REPORT
KB.KNOWLEDGE_ASSET
</span></span></code></div></div></pre>

👉 這個欄位是 **Memory / Vector / Ontology 的關鍵索引**

---

#### ▪️ input（可執行輸入）

<pre class="overflow-visible! px-0!" data-start="1389" data-end="1529"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(var(--sticky-padding-top)+9*var(--spacing))]"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>"input"</span><span>:</span><span></span><span>{</span><span>
  </span><span>"table"</span><span>:</span><span></span><span>"PURCHASE_ORDER"</span><span>,</span><span>
  </span><span>"filters"</span><span>:</span><span></span><span>{</span><span>
    </span><span>"date"</span><span>:</span><span></span><span>"2024-01-14"</span><span>
  </span><span>}</span><span>,</span><span>
  </span><span>"fields"</span><span>:</span><span></span><span>[</span><span>"po_no"</span><span>,</span><span></span><span>"item_code"</span><span>,</span><span></span><span>"qty"</span><span>]</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

> ❌ 禁止自然語言
>
> ✅ 必須能被「非 LLM 程式」消費

---

#### ▪️ context_refs（上下文不是貼上，而是引用）

<pre class="overflow-visible! px-0!" data-start="1606" data-end="1781"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(var(--sticky-padding-top)+9*var(--spacing))]"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>"context_refs"</span><span>:</span><span></span><span>[</span><span>
  </span><span>{</span><span>
    </span><span>"type"</span><span>:</span><span></span><span>"VECTOR"</span><span>,</span><span>
    </span><span>"ref_id"</span><span>:</span><span></span><span>"kb:purchase_schema:v3"</span><span>
  </span><span>}</span><span>,</span><span>
  </span><span>{</span><span>
    </span><span>"type"</span><span>:</span><span></span><span>"MEMORY"</span><span>,</span><span>
    </span><span>"ref_id"</span><span>:</span><span></span><span>"conv:20260129:purchase_query"</span><span>
  </span><span>}</span><span>
</span><span>]</span><span>
</span></span></code></div></div></pre>

👉 這正好吻合你「raw metadata 與 vector 分離」的設計。

---

#### ▪️ preconditions / postconditions（極關鍵）

<pre class="overflow-visible! px-0!" data-start="1874" data-end="2098"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(var(--sticky-padding-top)+9*var(--spacing))]"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>"preconditions"</span><span>:</span><span></span><span>[</span><span>
  </span><span>{</span><span></span><span>"type"</span><span>:</span><span></span><span>"SCHEMA_READY"</span><span>,</span><span></span><span>"ref"</span><span>:</span><span></span><span>"ERP.PURCHASE_ORDER"</span><span></span><span>}</span><span>
</span><span>]</span><span>,</span><span>
</span><span>"postconditions"</span><span>:</span><span></span><span>[</span><span>
  </span><span>{</span><span></span><span>"type"</span><span>:</span><span></span><span>"RESULT_SCHEMA_VALID"</span><span>,</span><span></span><span>"schema"</span><span>:</span><span></span><span>"PurchaseQueryResult"</span><span></span><span>}</span><span>,</span><span>
  </span><span>{</span><span></span><span>"type"</span><span>:</span><span></span><span>"ROW_COUNT_GT"</span><span>,</span><span></span><span>"value"</span><span>:</span><span></span><span>0</span><span></span><span>}</span><span>
</span><span>]</span><span>
</span></span></code></div></div></pre>

 **完成不是靠信任，是靠驗證** 。

---

## 3️⃣ Agent State Machine 規範（FSM）

### 🔹 3.1 狀態全集（不可擴充）

<pre class="overflow-visible! px-0!" data-start="2183" data-end="2298"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(var(--sticky-padding-top)+9*var(--spacing))]"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-text"><span><span>PENDING
DISPATCHED
RECEIVED
VALIDATING
PLANNING
EXECUTING
VERIFYING
COMPLETED
FAILED
NEED_HUMAN
ABORTED
</span></span></code></div></div></pre>

---

### 🔹 3.2 狀態轉移表（精簡但嚴格）

| Current    | Event         | Next       |
| ---------- | ------------- | ---------- |
| PENDING    | dispatched    | DISPATCHED |
| DISPATCHED | agent_ack     | RECEIVED   |
| RECEIVED   | input_valid   | VALIDATING |
| VALIDATING | ok            | PLANNING   |
| PLANNING   | plan_ready    | EXECUTING  |
| EXECUTING  | done          | VERIFYING  |
| VERIFYING  | pass          | COMPLETED  |
| VERIFYING  | fail          | FAILED     |
| FAILED     | retry_allowed | DISPATCHED |
| FAILED     | no_retry      | NEED_HUMAN |

> ⚠️ **Agent 不可跳狀態**

---

## 4️⃣ Agent 執行契約（Execution Contract）

每個 Agent 必須實作以下回報格式：

### 🔹 4.1 心跳（Heartbeat）

<pre class="overflow-visible! px-0!" data-start="2849" data-end="2981"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(var(--sticky-padding-top)+9*var(--spacing))]"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"todo_id"</span><span>:</span><span></span><span>"TODO-20260207-00031"</span><span>,</span><span>
  </span><span>"state"</span><span>:</span><span></span><span>"EXECUTING"</span><span>,</span><span>
  </span><span>"progress"</span><span>:</span><span></span><span>0.6</span><span>,</span><span>
  </span><span>"timestamp"</span><span>:</span><span></span><span>"2026-02-07T04:31:20Z"</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

---

### 🔹 4.2 產出物（Artifacts）

<pre class="overflow-visible! px-0!" data-start="3015" data-end="3150"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(var(--sticky-padding-top)+9*var(--spacing))]"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"type"</span><span>:</span><span></span><span>"DATASET"</span><span>,</span><span>
  </span><span>"format"</span><span>:</span><span></span><span>"JSON"</span><span>,</span><span>
  </span><span>"schema"</span><span>:</span><span></span><span>"PurchaseQueryResult"</span><span>,</span><span>
  </span><span>"location"</span><span>:</span><span></span><span>"s3://artifacts/todo-31.json"</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

---

### 🔹 4.3 錯誤回報（結構化）

<pre class="overflow-visible! px-0!" data-start="3179" data-end="3377"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(var(--sticky-padding-top)+9*var(--spacing))]"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"error_code"</span><span>:</span><span></span><span>"SQL_EXECUTION_FAILED"</span><span>,</span><span>
  </span><span>"message"</span><span>:</span><span></span><span>"Column item_code not found"</span><span>,</span><span>
  </span><span>"context"</span><span>:</span><span></span><span>{</span><span>
    </span><span>"sql"</span><span>:</span><span></span><span>"SELECT item_code FROM PO"</span><span>,</span><span>
    </span><span>"db"</span><span>:</span><span></span><span>"DuckDB"</span><span>
  </span><span>}</span><span>,</span><span>
  </span><span>"recoverable"</span><span>:</span><span></span><span>true</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

---

## 5️⃣ 失敗決策規範（給 Rule / Memory 用）

<pre class="overflow-visible! px-0!" data-start="3418" data-end="3707"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="sticky top-[calc(var(--sticky-padding-top)+9*var(--spacing))]"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-json"><span><span>{</span><span>
  </span><span>"on_fail"</span><span>:</span><span></span><span>[</span><span>
    </span><span>{</span><span>
      </span><span>"condition"</span><span>:</span><span></span><span>"error.recoverable == true"</span><span>,</span><span>
      </span><span>"action"</span><span>:</span><span></span><span>"RETRY"</span><span>
    </span><span>}</span><span>,</span><span>
    </span><span>{</span><span>
      </span><span>"condition"</span><span>:</span><span></span><span>"error_code == SCHEMA_MISMATCH"</span><span>,</span><span>
      </span><span>"action"</span><span>:</span><span></span><span>"DECOMPOSE"</span><span>
    </span><span>}</span><span>,</span><span>
    </span><span>{</span><span>
      </span><span>"condition"</span><span>:</span><span></span><span>"retry_exhausted"</span><span>,</span><span>
      </span><span>"action"</span><span>:</span><span></span><span>"ESCALATE"</span><span>
    </span><span>}</span><span>
  </span><span>]</span><span>
</span><span>}</span><span>
</span></span></code></div></div></pre>

👉 這裡非常適合接你之後的  **記憶抽象 + 經驗模型** 。

---

## 6️⃣ 一句架構級總結（你可以直接放文件）

> **Agent Todo 是一個具有狀態、條件與產出契約的工作單元；
>
> Agent 本身只是狀態機的執行者，而不是任務的擁有者。**
