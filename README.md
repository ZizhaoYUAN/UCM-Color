# UCM-Color 后台数据管理系统规划

## 0. 概述
面向连锁小超市的第一阶段（前台“无现金化 + 自助/无人收银”已就绪），本文件给出后台数据管理系统的整体规划：

- 需求分析（功能、非功能、角色与权限）
- 系统架构（逻辑、数据、部署）
- 操作流程图（商品、库存、会员、订单、营销、报表）
- 数据隔离与统计（每店独立维度 + 总部汇总）
- 本机一体化测试（Docker）与阿里云部署指引

系统采用模块化设计与开源技术栈：PostgreSQL（OLTP）、Redis（缓存）、ClickHouse（OLAP）、OpenSearch（全文检索/模糊搜索）、Kafka（事件流）。所有模块可独立部署与扩展。

---

## 1. 目标与范围
**目标：** 为总部与门店提供统一的主数据、交易与库存管理、会员与营销，以及可按“门店/区域/时段”维度的统计与分析能力；支撑前台自助收银稳定运行与回溯。

**本阶段范围（Phase‑1 后台）：**

- 基础主数据：商品、条码、类目、税率、价格表
- 库存管理：入库、出库、调拨、盘点（库存流水 Ledger + 可卖量 ATS）
- 会员/CRM：基础档案、标签、合并、积分（可选）
- 订单与结算：订单查询、状态流转、退款/作废、对账导出
- 营销与分析：基础折扣/满减/券（规则最小集），门店看板/日报/周报
- 系统能力：用户/角色/权限、审计日志、数据导入和导出与校验、用户登录

**KPI 指标：**

- 后台 API 可用性 ≥ 99.9%
- 关键查询（按商品/订单主键）P95 < 200ms
- 数据同步延迟（交易 → 报表）< 1 分钟（近实时）

---

## 2. 角色与权限

| 角色 | 职责 | 数据范围 |
| --- | --- | --- |
| 总部管理员（HQ Admin） | 全局配置、用户/角色、价格/促销发布、全量报表 | 全局 |
| 区域经理（Area Manager） | 本区域门店统计与审核 | 区域 |
| 门店经理（Store Manager） | 本店主数据维护（少量字段）、库存操作、订单售后 | 门店 |
| 稽核/财务（Audit/Finance） | 对账、导出、留痕审计 | 多店/全局（按授权） |
| 只读分析（BI Viewer） | 看板与导出 | 多店/全局（按授权） |

权限模型采用 **RBAC + 数据域（store_id/region_id）**，并使用 **PostgreSQL RLS（行级安全）** 实现后端强约束。

---

## 3. 功能需求

### 3.1 商品（Catalog）
- SKU/条码管理：多条码、包装规格、税率、产地、品牌、保质期属性
- 价格管理：标准价、会员价、生鲜临时调价（含生效时间）
- 批量导入/导出：CSV/Excel，导入前校验与预览差异
- 图片与富媒体：上传到对象存储（本机 MinIO / 云上 OSS）
- 商品查询和编辑

### 3.2 库存（Inventory）
- 库存流水 Ledger：入库、退货、报损、盘盈、调拨、销售扣减
- 盘点：差异对账、生成调整单
- 可卖量 ATS：在线计算 + 预聚合缓存
- 预警：低库存阈值、滞销告警
- 库存查询列表，导出和导入
- 门店商品库存调拨

### 3.3 会员（CRM）
- 会员档案：手机号、标签、黑名单、合并（重复号码、无效记录）
- 积分（可选）：获取、消费规则
- 隐私合规：脱敏展示、导出申请
- 会员等级设置和优惠配置
- 会员消费历史记录

### 3.4 订单（OMS/Orders）
- 查询/筛选：按时间、店、渠道、状态、会员、金额
- 状态流：`CREATED → PAID → READY → HANDED_OVER/DELIVERED → CLOSED`
- 售后：退款、作废（权限控制、双人复核可选）
- 对账：按渠道/支付方式汇总导出

### 3.5 营销与分析（Marketing & BI）
- 活动规则（最小集）：满减、折扣、券（可按门店/类目/会员等级）
- 报表与看板：销售额、客单价、UPT、毛利（估算）、TOPN 商品、时段热力
- 门店/区域多维透视：`store_id` 分区 + 物化视图刷新（分钟级）

### 3.6 系统（System）
- 用户、角色、权限、API 密钥、审计日志（谁在何时做了什么）
- 任务：导入任务、批处理、定时刷新
- 用户登录和验证

---

## 4. 非功能需求
- **可靠性：** 多副本数据库、备份/恢复演练、主从切换
- **一致性：** OLTP 侧强一致（PostgreSQL 事务），OLAP 侧最终一致（CDC → ClickHouse）
- **性能：** 热查询走 Redis 缓存/ClickHouse 聚合；表按 store_id/time 分区
- **安全：** TLS、RLS、最小权限、审计追踪；敏感列加密（如手机号）
- **可观测性：** 日志（Loki/SLS）、指标（Prometheus/ARMS）、分布式 TraceID

---

## 5. 领域模型（简化 ER）
```mermaid
erDiagram
  STORE ||--o{ USER : has
  STORE ||--o{ ORDER : owns
  STORE ||--o{ STOCK_LEDGER : owns
  STORE ||--o{ PRICE : owns
  SKU ||--o{ BARCODE : has
  SKU ||--o{ PRICE : priced_by
  ORDER ||--|{ ORDER_ITEM : contains
  MEMBER ||--o{ ORDER : places

  STORE { string store_id PK }
  SKU { string sku_id PK, string name, string brand, string category, float tax_rate }
  BARCODE { string code PK, string sku_id FK }
  PRICE { string store_id FK, string sku_id FK, decimal price, datetime start_at, datetime end_at }
  STOCK_LEDGER { bigint id PK, string store_id, string sku_id, int qty_delta, string reason, datetime ts }
  ORDER { string order_id PK, string store_id, string channel, string status, string member_id, decimal total, datetime created_at }
  ORDER_ITEM { string order_id FK, string sku_id, int qty, decimal price, float tax_rate }
  MEMBER { string member_id PK, string phone, string tier, jsonb tags }
```

---

## 6. 系统架构

### 6.1 逻辑架构（模块化）
```mermaid
flowchart LR
  subgraph AdminUI[后台管理前端 SPA]
    UI[React/Vue SPA]
  end
  subgraph AdminAPI[后台管理 API]
    AUTH[Auth/RBAC]
    CAT[Catalog]
    INV[Inventory]
    OMS[Orders]
    CRM[Members]
    MKT[Marketing]
    RPT[Reporting]
  end
  MQ[(Kafka)]
  REDIS[(Redis Cache)]
  PG[(PostgreSQL OLTP)]
  CK[(ClickHouse OLAP)]
  OS[(OpenSearch)]
  OBJ[(对象存储: 本机 MinIO / 云上 OSS)]

  UI<-->AdminAPI
  AdminAPI<-->PG
  AdminAPI<-->REDIS
  AdminAPI--全文检索-->OS
  AdminAPI--上传图片-->OBJ
  AdminAPI--事件-->MQ
  MQ-->ETL[CDC/Stream ETL]
  ETL-->CK
```

说明：命令/查询分离（CQRS），写入走 PostgreSQL；分析类查询走 ClickHouse；全文检索走 OpenSearch。事件驱动：写入后产生业务事件（`SKU_UPDATED`、`STOCK_MOVED`、`ORDER_PAID`），供 ETL 或异步处理（如券核销、报表刷新）。

### 6.2 部署架构（本机 → 阿里云）
```mermaid
flowchart TB
  subgraph Local[本机一体化测试]
    DockerCompose((Docker Compose))
    DockerCompose-->AdminUI
    DockerCompose-->AdminAPI
    DockerCompose-->PG
    DockerCompose-->REDIS
    DockerCompose-->CK
    DockerCompose-->OS
    DockerCompose-->MQ
    DockerCompose-->MinIO
  end

  subgraph Aliyun[阿里云]
    SLB[SLB/API Gateway]
    EcsApi[ECS/ACK: AdminAPI]
    EcsUi[ECS/OSS: AdminUI]
    RDS[(ApsaraDB for PostgreSQL)]
    Redis[(ApsaraDB for Redis)]
    Kafka[(消息队列 Kafka 版)]
    CH[(ClickHouse on ECS 或 ApsaraDB for ClickHouse)]
    OpenSearch[(OpenSearch/ES 服务)]
    OSS[(对象存储 OSS)]
  end

  Local --> |镜像/配置迁移| Aliyun
  SLB-->EcsUi
  SLB-->EcsApi
  EcsApi-->RDS
  EcsApi-->Redis
  EcsApi-->Kafka
  Kafka-->CH
  EcsApi-->OpenSearch
  EcsApi-->OSS
```

---

## 7. 每店数据独立统计与隔离
推荐策略：单库单 Schema 承载所有门店，主表均含 `store_id`，同时：

- **RLS（Row‑Level Security）：** 按登录用户的 `store_id`/`region_id` 限定可见行；
- **分区：** 按 `(store_id, ts)` 组合分区（或时间分区 + `store_id` 索引），提升查询与冷热分层；
- **物化视图：** ClickHouse 侧建立 `sales_daily_mv`、`topn_sku_mv`，1 分钟内 CDC 增量到位。

**RLS 示例（PostgreSQL）**
```sql
-- 1) 在 role 上挂用户的门店列表（会话级 GUC 或映射表）
CREATE TABLE user_store_scope(uid uuid, store_id text);
-- 2) 开启 RLS
ALTER TABLE "order" ENABLE ROW LEVEL SECURITY;
-- 3) 针对角色定义策略：仅可访问与自己绑定的 store
CREATE POLICY p_order_by_store ON "order" USING (
  EXISTS (
    SELECT 1
    FROM user_store_scope s
    WHERE s.uid = current_user AND s.store_id = "order".store_id
  )
);
```
> 生产中可将 `current_user` 替换为 `current_setting('app.user_id')`，由 API 层在连接池上设置。

**ClickHouse 分区示例**
```sql
CREATE TABLE sales_fact (
  store_id String,
  sku_id String,
  qty Int32,
  amt Decimal(12,2),
  ts DateTime
) ENGINE = MergeTree()
PARTITION BY toYYYYMM(ts)
ORDER BY (store_id, ts);
```

---

## 8. 后台管理 UI（现代高效交互）

- **技术栈：** React + Vite + Ant Design（或 Arco Design），前后端分离。
- **信息架构：**
  - 顶部：系统/店铺切换、全局搜索、通知、用户头像
  - 侧栏：仪表盘 / 商品 / 价格 / 库存 / 订单 / 会员 / 营销 / 报表 / 系统
  - 列表页：列配置、筛选保存、批量操作、导入/导出、操作留痕
  - 明细页：分区卡片（基础信息/图片/价格/库存/日志）
- **典型页面：**
  - 仪表盘：今日 GMV、客单、UPT、支付成功率、TOPN 商品、门店对比
  - 商品管理：列表 + 多条码 + 图片上传（OSS/MinIO）+ 价格时序
  - 库存管理：库存总览、流水、盘点单、预警
  - 订单中心：列表 + 详情（状态流/支付/小票）+ 售后处理
  - 会员中心：档案、标签、订单与行为、合并/黑名单
  - 营销：活动/券规则、适用范围（门店/类目/会员群）
  - 报表：门店日报/周报、时段热力、活动效果
  - 系统设置：用户/角色/RLS 绑定、API Key、审计日志

---

## 9. 关键流程图

### 9.1 商品上新（导入 → 校验 → 发布）
```mermaid
flowchart TD
  A[导入CSV/Excel] --> B[字段映射与校验]
  B -->|通过| C[预览差异]
  B -->|失败| B1[下载错误报告]
  C --> D{生效范围?}
  D -->|总部| E[写入SKU/条码/价格]
  D -->|指定门店| E
  E --> F[发事件 SKU_UPDATED]
  F --> G[刷新缓存/搜索索引]
```

### 9.2 库存操作（流水 + ATS）
```mermaid
sequenceDiagram
  participant UI as Admin UI
  participant INV as Inventory API
  participant PG as PostgreSQL
  participant MQ as Kafka
  UI->>INV: 提交入库/调拨/盘点
  INV->>PG: 写入 STOCK_LEDGER（事务）
  INV-->>UI: 成功/失败
  INV->>MQ: 发送 STOCK_MOVED 事件
  MQ->>CK: ETL 更新销售/库存汇总
  Note over INV: ATS=OnHand-Reserved+InTransit
```

### 9.3 订单售后
```mermaid
flowchart LR
  A[查询订单] --> B{可退款/作废?}
  B -- 否 --> X[终止]
  B -- 是 --> C[提交售后申请]
  C --> D[权限/双人复核]
  D --> E[写入退款单/订单状态]
  E --> F[发事件 ORDER_REFUNDED]
  F --> G[对账与报表刷新]
```

### 9.4 报表近实时链路（CDC/事件）
```mermaid
flowchart LR
  PG[(PostgreSQL)] -- WAL/CDC --> Debezium
  Debezium --> Kafka
  Kafka --> ETL[Stream Processor]
  ETL --> CK[(ClickHouse)]
  CK --> BI[Dashboard/Report]
```

---

## 10. 本机测试环境（示例 Docker Compose）
仅示意，端口可按需调整；Admin API/前端可用现有基座或快速脚手架（FastAPI/Node + React）。

```yaml
version: '3.8'
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: retail
      POSTGRES_PASSWORD: retail
      POSTGRES_DB: retail
    ports: ["5432:5432"]
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
  clickhouse:
    image: clickhouse/clickhouse-server:24.8
    ports: ["9000:9000","8123:8123"]
  opensearch:
    image: opensearchproject/opensearch:2
    environment: { "discovery.type": single-node, "DISABLE_SECURITY_PLUGIN": "true" }
    ports: ["9200:9200","9600:9600"]
  zookeeper:
    image: bitnami/zookeeper:3.9
    environment: { ALLOW_ANONYMOUS_LOGIN: "yes" }
  kafka:
    image: bitnami/kafka:3.7
    environment:
      KAFKA_CFG_ZOOKEEPER_CONNECT: zookeeper:2181
      ALLOW_PLAINTEXT_LISTENER: "yes"
    ports: ["9092:9092"]
    depends_on: [zookeeper]
  minio:
    image: minio/minio
    command: server /data --console-address :9001
    environment: { MINIO_ROOT_USER: admin, MINIO_ROOT_PASSWORD: admin123 }
    ports: ["9000:9000","9001:9001"]
  admin-api:
    image: yourorg/admin-api:dev
    environment:
      DB__CONN: postgres://retail:retail@postgres:5432/retail
      REDIS__CONN: redis:6379
      CK__HTTP: http://clickhouse:8123
      OS__URL: http://opensearch:9200
      KAFKA__BROKERS: kafka:9092
    ports: ["8080:8080"]
    depends_on: [postgres,redis,clickhouse,opensearch,kafka]
  admin-ui:
    image: yourorg/admin-ui:dev
    ports: ["3000:80"]
    depends_on: [admin-api]
```

**基本验证脚本：**

1. `GET /health`（API、DB 连接）
2. 创建 SKU → 查询 → 更新价格 → 搜索索引可用
3. 入库/出库 → Ledger 有记录 → ATS 刷新 → BI 表更新（ClickHouse）
4. 订单查询 → 售后 → 对账导出（CSV）

### 10.1 后台系统测试策略

为了保障后台系统在多模块、多数据源场景下的稳定性，建议构建分层测试体系，并纳入 CI/CD 流程：

- **静态质量门禁：** 在提交阶段运行代码规范（ESLint/Prettier、flake8 等）和类型检查（TypeScript、mypy），配合检测开放接口的 OpenAPI/JSON Schema 变更。
- **单元测试（Unit）：** 后端模块（Catalog/Inventory/OMS/CRM 等）分别覆盖核心领域逻辑、权限判断、计算公式（如 ATS 计算、积分规则），目标用例覆盖率 ≥ 80%。
- **契约测试（Contract）：** 通过 Pact/OpenAPI Mock 校验 Admin UI、第三方对接系统对 API 的请求/响应格式，避免接口回归导致前后端耦合问题。
- **集成测试（Integration）：** 基于 Docker Compose 环境启动 PostgreSQL/Redis/ClickHouse/Kafka/OpenSearch，执行跨模块流程（导入商品、库存调拨、售后退款），校验事件与数据链路是否完整。
- **端到端测试（E2E）：** 使用 Playwright/Cypress 模拟真实用户操作后台 UI（商品维护、库存盘点、售后审批），结合测试账号的 RLS 数据域验证权限隔离。
- **性能与容量测试：** 借助 k6/JMeter 回放高并发下的关键 API（订单查询、库存扣减、商品搜索），观察 P95 时延、Redis 命中率、数据库锁等待；按门店规模（10/50/100）逐级压测。
- **数据质量与同步：** 定期对比 PostgreSQL 与 ClickHouse 汇总结果，使用校验作业（dbt/Great Expectations）检测指标异常；Kafka 消费延迟纳入监控，触发告警。
- **安全测试：** 进行权限绕过、RLS 验证、敏感数据脱敏检查；对管理端登录流程执行弱口令扫描与 MFA 验证。
- **回归与发布验收：** 在每次上线前执行冒烟套件（健康检查、关键业务链路）并生成报告；灰度环境与生产环境接入同一套监控仪表盘，确认指标无异常后再全量发布。

---

## 11. 阿里云部署（从本机到云端）
**建议路径：**

1. **P0 试点（单区）：** ECS 2 台（API/UI）、RDS for PostgreSQL、ApsaraDB Redis、消息队列 Kafka 版、OSS、ClickHouse on ECS；前面挂 SLB。
2. **P1 扩容：** 迁移 API/UI 到 ACK（Kubernetes），接入 ARMS/日志服务 SLS；ClickHouse 采用 ApsaraDB for ClickHouse 或 ECS 组网分片。

**关键步骤：**

- 创建 VPC/安全组（放通 80/443，数据库仅内网）
- RDS PG：开启自动备份，设置参数与扩展（pg_trgm/jsonb/gist/ginx）
- Redis：开通持久化，设置键空间告警
- Kafka：创建 Topic（`SKU_UPDATED` / `STOCK_MOVED` / `ORDER_*`）
- OpenSearch：建索引模板（SKU 名称/条码/品牌/分词）
- ClickHouse：建聚合表与物化视图；ETL（Debezium/Flink 或自研消费者）
- CI/CD：镜像推送 ACR；ACK/ECS 部署，注入 `APP__*` 环境变量与 Secret
- 观测：ARMS + SLS + Prometheus/Grafana，看板包含 QPS/RT/错误率/队列滞留/ETL 延迟

---

## 12. 数据接口与事件（最小 Schema）

**事件 Topic**

- `sku.updated` `{ sku_id, changed_fields, ts }`
- `stock.moved` `{ store_id, sku_id, qty_delta, reason, ref_id, ts }`
- `order.paid` `{ order_id, store_id, total, member_id, channel, ts }`
- `member.updated` `{ member_id, tags, ts }`

**REST 示例**

- `POST /catalog/sku`、`PUT /catalog/sku/{id}`、`GET /catalog/sku?store_id=&q=`
- `POST /inventory/move`（入库/出库/盘点统一入口，枚举 reason）
- `GET /orders?store_id=&status=&from=&to=`、`POST /orders/{id}/refund`
- `POST /members/merge`、`GET /members/{id}`

---

## 13. 报表与看板（ClickHouse）

- `sales_daily(store_id, day, amt, qty, txn_cnt, aov, upt)`
- `sales_by_hour(store_id, hour, amt)`
- `topn_sku(store_id, day, sku_id, rank, amt, qty)`
- `refund_rate(store_id, day, rate)`

> 通过物化视图/定时任务（1 分钟）增量刷新；Admin UI 端做下钻与筛选保存。

---

## 14. 风险与缓解
- 导入脏数据 → 预校验 + 回滚、错误报告
- 价格/库存并发 → 串行化关键事务 + 乐观锁
- 跨模块一致性 → 事件溯源 + 幂等键（order_id/tx_id）
- 店铺隔离 → RLS + 最小权限 + 审计
- 报表延迟 → 监控 ETL 滞留，降级到近实时缓存

---

## 15. 里程碑（建议）
- **M0（T+2 周）：** 本机一体化跑通，完成 20 条验收用例
- **M1（T+6 周）：** 阿里云试点 2–3 家店，日报/周报正确
- **M2（T+10 周）：** 扩至 10+ 店，完成权限/RLS、全链路监控与备份演练

---

## 16. 支付模块
- 预留支付接口，支持国内主流支付平台对接（如财富通）。
- 后台支持查询支付记录，提供日/月度支付数据统计。
