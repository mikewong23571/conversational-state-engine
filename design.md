# 对话驱动的状态维护与产物生成系统（CSE）——设计文档 v0.1

> Conversation-driven State Engine (CSE)

**状态：可实现的详细设计**\
**目标读者：** 架构师、后端/前端工程师、产品/项目经理、测试与运维\
**版本：** v0.1（MVP 基线）

---

## 0. 摘要

CSE 通过对话把“用户需求/目标”可靠地转译为“可审计的状态变更（JSON Patch）”，并在渐进式确认后形成提交（Commit），由渲染器生成最终产物（文档/表格/代码等）。系统强调：单一事实源（Canonical State）、版本化、可回滚、冲突检测、可观测性与可扩展性（多场景、多 Agent）。

---

## 1. 目标与非目标

### 1.1 目标

- **对话 → 意图 → Patch → 渐进式确认 → Commit → Artifact** 的可追溯流水线。
- **确定性优先**：命令通道覆盖常用 CRUD；自然语言由解析器+校验兜底。
- **可审计**：版本化、Diff、影响分析（Impact Analysis）、冲突检测（结构+逻辑）。
- **可扩展**：Schema 演化、插件式渲染、多 Agent 协作、实时编辑预留。

### 1.2 非目标（MVP）

- 不内置复杂流程编排与跨系统自动化（仅留扩展点）。
- 不做大规模多人协同冲突自动化深度处理（先人审后合）。
- 不提供强依赖外部 SaaS 的功能（内网/本地优先）。

---

## 2. 概念模型

- **Session**：对话与状态的容器。
- **State**：规范状态（JSON），受 **Schema** 约束。
- **Schema**：JSON Schema + 自定义不变量校验器。
- **Intention**：结构化意图（action/target\_path/value/reason/confidence）。
- **Patch**：RFC6902 JSON Patch；以事务批量应用。
- **ImpactAnalysis**：受影响路径、风险等级、语义/逻辑冲突、建议修复。
- **Commit**：被确认的补丁集（含逆补丁、作者、时间、父指针）。
- **Artifact**：从 State 渲染出的产物（Markdown/CSV/Docx/…）。
- **Policy**：权限与变更策略（RBAC/ABAC/字段级）。

---

## 3. 总体架构

```
┌──────────┐   Message   ┌───────────────┐   IntentionSet   ┌───────────┐
│  Client  │ ─────────▶ │ DialogueAnalyzer│ ───────────────▶│ PatchPlanner│
└──────────┘            └──────┬─────────┘                   └─────┬─────┘
                                │  ContextSlice                     │ Patches
                                │                                   ▼
                           ┌─────▼─────┐                      ┌──────────────┐
                           │ Validator │◀── Schema/Rules ──── │ImpactAnalyzer│
                           └─────┬─────┘                      └─────┬────────┘
                                 │                                    │
                                 ▼ Progressive Confirmation            │
                           ┌───────────────┐                           │
                           │ Confirm Engine│                           │
                           └─────┬─────────┘                           │
                                 │ Commit                               │
                                 ▼                                      ▼
                           ┌──────────────┐                      ┌─────────────┐
                           │   Versioned  │◀───── Txn ─────────▶ │  Renderer   │
                           │   StateStore │                      │ (Incremental)│
                           └──────────────┘                      └─────────────┘
```

---

## 4. 组件设计

### 4.1 DialogueAnalyzer（解析器：Analyzer → Planner → Interpreter）

- **命令通道**：`/add /edit /del /move /set /link` 确定性解析（PEG/正则）。
- **自然语言通道**：few-shot + 严格 JSON 输出（function calling/Schema 校验）。
- **规范化**：同义词映射、路径补全、默认值、枚举合法化。
- **校验**：路径存在性、Schema 校验、冲突前置检测（候选状态）。

#### 数据模型（精简）

```json
Intention = {
  "action": "add|modify|delete|move|set",
  "target_path": "/stories/-",
  "value": {...},
  "reason": "string",
  "confidence": 0.85
}
```

### 4.2 ContextSlicer（上下文智能裁剪）

- 倒排索引（token→pointer）+ 关系图（依赖一度扩展）。
- 预算控制：`max_items`、`max_bytes`，附 `_meta` 摘要。
- 输入：消息 + full\_state；输出：与意图相关的子树（state\_slice）。

### 4.3 PatchPlanner（补丁规划）

- 将意图集映射为最小 RFC6902 补丁集；相邻替换合并；同事务提交。
- 支持 **BatchIntention**：受控 JSONPath 扩展（仅 `modify|set` 合法）。

### 4.4 ImpactAnalyzer（影响与冲突）

- **结构冲突**：路径/类型/枚举/引用断裂。
- **逻辑冲突**（V1 规则集）：
  - 认证互斥：`auth_type=SSO` 不得同时要求本地口令；
  - 依赖优先级：被依赖项优先级不得低于依赖方；
  - 时间线一致性：`end_date` > `start_date`。
- **近似重复**：V1.1 提示级（本地向量索引）。
- 输出：`affected_paths/risk_level/semantic_conflicts/suggested_alternatives`。

### 4.5 Confirm Engine（渐进式确认状态机）

- **阶段**：Intent → Change（Diff 勾选）→ Side-Effect（警告+自动修复）。
- 每阶段可取消/返回；通过后进入下一阶段；最终生成 Commit。

### 4.6 Versioned StateStore（版本化存储）

- SQLite（MVP）→ Postgres（生产）；
- 表：`sessions/states/draft_intentions/patch_proposals/commits/artifacts`；
- 事务：补丁组原子应用；保存 `reverse_patches`；可回滚。

### 4.7 Renderer（增量渲染）

- 片段缓存：`fragment_id -> rendered_fragment`；
- 依赖映射：`path_prefix -> [fragment_ids]`；
- 仅重渲染受影响片段，最后装配输出。

### 4.8 Realtime（可选，接口预留）

- 文本域用 Yjs/CRDT；结构域仍走 Patch/PR 流程；
- 双向桥：`yjs_update <-> json_patch`，拒绝越权结构改写。

---

## 5. 数据与存储设计

### 5.1 SQLite 表结构（MVP）

```sql
CREATE TABLE sessions (
  sid TEXT PRIMARY KEY,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE states (
  sid TEXT,
  version TEXT,
  schema_version TEXT,
  json TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (sid, version)
);

CREATE TABLE draft_intentions (
  id TEXT PRIMARY KEY,
  sid TEXT,
  json TEXT NOT NULL,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE patch_proposals (
  id TEXT PRIMARY KEY,
  sid TEXT,
  intentions_id TEXT,
  patches_json TEXT NOT NULL,
  impact_json TEXT,
  preview_diff_json TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE commits (
  id TEXT PRIMARY KEY,
  sid TEXT,
  parent_version TEXT,
  version TEXT,
  patches_json TEXT NOT NULL,
  reverse_patches_json TEXT NOT NULL,
  author TEXT,
  message TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE artifacts (
  id TEXT PRIMARY KEY,
  sid TEXT,
  version TEXT,
  type TEXT,
  url TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### 5.2 索引与搜索

- stories 的 `key/title/acceptance` 建 FTS5；
- 指针索引：对象数组建立 `key→pointer` 的二级索引，O(1) 访问；
- 依赖图：`key -> [deps]`；反向图用于影响分析。

---

## 6. API 设计（OpenAPI 3.1 摘要）

> 完整 YAML 参见仓库 `/api/openapi.yaml`（该文件可由本文复制起步）。

- `GET /sessions/{sid}/state?paths=...`：获取 Canonical State（支持切片）。
- `POST /sessions/{sid}/intents`：提交草案意图（或由服务端解析生成）。
- `POST /sessions/{sid}/patch-proposals`：从意图规划补丁并生成影响分析与预览差异。
- `POST /sessions/{sid}/confirm?stage=intent|change|side_effect`：分步确认。
- `POST /sessions/{sid}/commit`：原子提交补丁，生成新版本并触发渲染。
- `GET /sessions/{sid}/artifacts[?version=]`：列举/获取产物。
- **可选**：`POST /schema/migrate`、`POST /batch/expand`（仅内网管理用途）。

### 6.1 错误响应规范

```json
{
  "error": {
    "code": "VALIDATION_FAILED|CONFLICT|UNAUTHORIZED|NOT_FOUND|RATE_LIMIT",
    "message": "human readable",
    "details": {"path":"/stories/3/title", "expected":"string", "actual":42}
  },
  "correlation_id": "uuid"
}
```

---

## 7. 权限与策略（Security & Policy）

- **RBAC**：`Admin/Reviewer/Editor/Viewer`；
- **ABAC**：属性规则（模块、冻结窗口、环境标签）；
- **字段级**：敏感字段脱敏/只读（如 `/constraints/*` 仅 Admin 可改）。
- **补丁门禁**：在 `patch-proposals` 阶段预授权；未授权补丁不可勾选。
- **审计**：记录 actor/policy\_checks/决策摘要；产出变更日志。

---

## 8. 解析与裁剪实现细节

### 8.1 命令通道语法（示例）

```
/add story key=AUTH-Login priority=P0 platform=[iOS,Android] reason="移动端+生物识别"
/edit story key=AUTH-Login set priority=P1
/del story key=AUTH-Old
/set stories[$key==AUTH-Login].auth_type=SSO
```

### 8.2 自然语言通道约束

- System 提示固定职责与输出 **仅 JSON**；
- User 内容仅包含必要 Schema 片段 + Context Slice；
- 产出 `IntentionSet`，无法映射时返回 `unknown` 并附澄清建议。

### 8.3 ContextSlicer 策略

- 关键词（BM25/TF-IDF）+ 词典（领域同义词）。
- 一度关联：依赖与被依赖。
- 限流：最大对象数、最大字节、字段白名单。

---

## 9. 冲突检测与影响分析

### 9.1 结构冲突

- 路径不存在/不可写；类型/枚举违规；引用断裂（删除被引用 key）。

### 9.2 逻辑冲突（规则引擎）

- `auth_method_conflict` / `dependency_order` / `timeline_consistency`。
- 返回 `severity: high|medium|low` 与建议修复 `suggestion`（自动修复候选 Patch）。

### 9.3 近似重复（V1.1）

- 本地向量库（FAISS/SQLite-vec）；Text fields：title/acceptance。

---

## 10. 渐进式确认（状态机）

**阶段与接口：**

1. `intent`：复述意图；允许返回修改意图或取消。
2. `change`：展示 Diff（分组：add/modify/delete）；逐条勾选。
3. `side_effect`：展示风险与 auto-fix；可勾选应用。

**失败回退**：任意阶段失败或取消均不污染 Canonical State。

---

## 11. Schema 演化

- 语义化版本；迁移脚本 `up/down`（纯函数）。
- 自动建议：统计校验失败模式，产生 Schema 优化建议（人工决策）。

---

## 12. 性能与可扩展性

- **大状态优化**：分区/惰性加载；`GET /state?paths=` 局部拉取。
- **索引**：指针索引 + FTS5；
- **Diff/渲染**：子树增量；前端虚拟滚动；
- **事务**：补丁批量原子应用；渲染异步，缓存 `(version, template)`。

目标指标（MVP，单机参考）：

- 典型提交（≤20 patch）端到端 P95 < 500ms（不含远程 LLM）；
- 大状态（stories=5k）局部 Diff 预览 < 300ms；
- 渲染片段更新 P95 < 200ms。

---

## 13. 观测与运维

- OpenTelemetry：`draft_intents / propose_patches / commit` 3 个 span；
- 关键指标：patch 数、风险等级分布、拒绝率、渲染耗时；
- 结构化日志：附 `sid/user/proposal_id/version`；
- 健康检查：`/healthz`，含 DB 连接与磁盘配额。

---

## 14. 安全与合规

- 认证：Token（MVP）→ OIDC（生产）；
- 授权：服务端强制；
- 审计追踪：不可篡改日志（可选 WORM 介质）；
- 数据主权：内网优先，外联（LLM）可禁用或走代理/本地模型；
- 数据保留：可配置 TTL/归档策略。

---

## 15. 测试策略

- **单测**：解析/裁剪/规则/补丁/逆补丁/迁移/渲染片段。
- **集成**：端到端 5 条典型用例（新增登录、批量改优先级、删除被引用项、时间线修复、Schema 迁移）。
- **回归**：对每条规则提供正/反例；
- **性能**：基准集（1k/5k/10k stories）。

---

## 16. 部署与配置

- 形态：Docker Compose（API+DB+静态前端）；
- 配置：
  - `CSE_DB_URL=sqlite:///data/cse.db`
  - `CSE_FEATURE_BATCH=true|false`
  - `CSE_FEATURE_DUPCHECK=true|false`
  - `CSE_RENDER_CACHE_DIR=/data/cache`
  - `CSE_LLM_PROVIDER=mock|openai|vllm`
  - `CSE_MAX_SLICE_BYTES=64000`

---

## 17. 风险、回滚与缓解

- **解析歧义**：命令通道优先；自然语言阶段强制二次确认。
- **批量误操作**：仅允许受控字段批改；默认不开启删除/移动。
- **复杂合并**：结构域由补丁控制；文本域 CRDT，冲突保守上报人审。
- **渲染一致性**：以 `version` 为输入；渲染失败不影响 commit（重试队列）。

---

## 18. MVP 范围与里程碑

- **M0（本文 v0.1）**：
  - 跑通闭环：解析（含命令）→ 补丁+影响 → 渐进式确认 → 提交 → 增量渲染；
  - 规则三条 + 权限 RBAC + 基础审计；
  - OpenTelemetry & 结构化日志。
- **M1**：批量意图（受控 JSONPath）、相似项检测（提示）、Schema 迁移工具链；
- **M2**：实时协作桥、丰富 Renderer 模板、外部导出（Docx/PDF）。

---

## 19. 附录

### 19.1 示例业务 Schema（需求文档）

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "metadata": {"type":"object","properties":{
      "version":{"type":"string"},
      "last_modified":{"type":"string","format":"date-time"}
    }},
    "stories": {"type":"array","items":{"$ref":"#/definitions/story"}},
    "glossary": {"type":"array","items":{"type":"object"}}
  },
  "definitions": {
    "story": {"type":"object","required":["key","title","acceptance_criteria"],
      "properties":{
        "key":{"type":"string","pattern":"^[A-Z]+-[A-Z0-9]+$"},
        "title":{"type":"string"},
        "priority":{"enum":["P0","P1","P2"]},
        "auth_type":{"enum":["local","SSO"],"nullable":true},
        "dependencies":{"type":"array","items":{"type":"string"}},
        "acceptance_criteria":{"type":"array","items":{"type":"string"},"minItems":1},
        "start_date":{"type":"string","format":"date"},
        "end_date":{"type":"string","format":"date"}
      }
    }
  }
}
```

### 19.2 OpenAPI（精简）

见第 6 节摘要，可直接导出为 `/api/openapi.yaml`。

### 19.3 端到端用例（摘）

- 输入消息：新增登录故事（移动+生物识别、P0，依赖 AUTH-SSO）。
- 解析 → 意图 → Patch：`add /stories/- {...}`。
- 影响：`risk=medium` + 逻辑冲突（若含本地口令条目）。
- 渐进式确认：勾选自动修复；提交生成 `v12`；产物增量更新。

---

## 20. 结语

本设计强调“确定性主干 + 智能增益”，优先打通从对话到产物的最短路径，在工程上保证可审计与可回滚。随后的功能（批量、相似项、协同、更多模板）均已预留接口与扩展点，可按里程碑逐步演进。

