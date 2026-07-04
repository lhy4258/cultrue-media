# AI 评价生成 Demo 本地交付文档

## 1. 项目概述

本项目实现了一个本地运行的移动端 H5 Demo，用于帮助 Sunny Tea House 顾客快速生成平台评价或推荐文案。用户选择 1-2 个消费感受，再选择 Google 或小红书，前端请求 FastAPI 后端调用真实大模型生成内容。用户可以继续手动编辑正文，然后一键复制，并在页面内查看企业微信 Webhook 的 mock 请求拼装结果，最后跳转到对应平台入口。

当前交付模式为：

- 前端：Vue 3 + Vite 移动端 H5，本机访问 `http://127.0.0.1:5173`。
- 后端：Python FastAPI，本机访问 `http://127.0.0.1:8000`。
- 模型：后端读取 `backend/.env` 中的模型环境变量，调用 OpenAI-compatible 模型接口。
- 企业微信：不接入真实企业微信群机器人，改为纯前端 mock 演示 Webhook 数据拼装与调用逻辑。
- 数据库：本地 Docker PostgreSQL 已预留 `reviews` 表和 `/api/incoming-review` 接口；当前主流程不依赖数据库。

本地地址：

```text
前端页面：http://127.0.0.1:5173
后端接口：http://127.0.0.1:8000
后端健康检查：http://127.0.0.1:8000/api/health
```

说明：本项目已解除 Render 后端和 PinMe 前端部署，文档与配置已改回本机回环地址。

## 2. AI 辅助编程工具使用策略

本项目使用 Codex 参与需求阅读、方案拆解、代码实现、调试验证和交付文档整理。AI 工具主要承担高重复度、结构化和跨文件联动工作，关键技术路线和范围调整由人工确认。

AI 参与内容：

- 从需求文档中提取核心闭环：选择感受、选择平台、生成评价、用户编辑、复制、跳转平台、Webhook 演示。
- 规划前后端分离结构，前端使用 Vue/Vite，后端使用 FastAPI。
- 编写后端单元测试，覆盖平台校验、感受数量限制、Prompt 选择、空模型返回重试、Webhook 预留逻辑和 PostgreSQL 预留仓库。
- 搭建移动端页面，补充 loading、失败提示、复制失败提示、后退后可继续操作、生成后只能手动修改等状态。
- 整理本地启动命令、依赖导入路径、接口地址、未完成项和本交付文档。

人工确认内容：

- 真实模型可以接入。
- 真实企业微信不接入，改为纯前端 mock 展示 Webhook 拼装逻辑。
- 已解除线上 Render/PinMe 部署，项目恢复为本地回环访问。
- 当前生成接口不再设置 `max_tokens`，只在内部 Prompt 中限制输出字数范围。

## 3. 功能实现说明

### 3.1 前端功能

前端主页面实现了完整移动端流程：

- 消费感受标签：最多选择 2 个，至少选择 1 个才允许生成。
- 平台切换：Google 和小红书两种模式。
- 生成内容：调用后端 `/api/generate-review-stream`，模型文本以流式片段实时追加到文本框；生成成功后锁定生成按钮，后续只能手动编辑。
- 可编辑正文：用户可以直接修改 AI 生成内容，最终发布内容不限制长度。
- 复制并模拟 Webhook：复制正文后，在前端构造企业微信机器人 Markdown 请求体，并展示请求方式、模拟地址、中文摘要、回复草稿和 JSON body。
- 打开发布入口：Google 打开 Google Maps/Search 入口，小红书打开网页入口，不做内容预填。
- 页面后退恢复：从平台入口后退回评价页面后，仍可再次点击“打开发布入口”和“复制并模拟 Webhook”。

### 3.2 后端接口

后端提供以下接口：

```text
GET /api/health
POST /api/generate-review
POST /api/generate-review-stream
POST /api/notify-wecom
POST /api/incoming-review
```

当前主流程实际使用：

```text
GET /api/health
POST /api/generate-review-stream
```

`POST /api/generate-review-stream` 请求示例：

```json
{
  "feelings": ["服务好"],
  "platform": "google"
}
```

流式响应示例：

```text
event: chunk
data: {"text":"Generated"}

event: chunk
data: {"text":" review text"}

event: done
data: {"platform":"google"}
```

`/api/generate-review` 是保留的非流式兼容接口。`/api/notify-wecom` 和 `/api/incoming-review` 是后续真实评论来源或真实企微扩展的预留能力。当前前端不调用真实企微接口，企业微信演示全部在前端 mock 完成。

## 4. Prompt 设计与调优过程

后端按平台拆分两套评价生成 Prompt。

Google Prompt 目标：

- 输出英文评价。
- 使用北美真实消费者口吻。
- 内容客观、自然、具体，不像广告。
- 输出不少于 50 个英文字符，最多 100 个英文字符。
- 不提 AI、提示词、折扣或任务说明。

小红书 Prompt 目标：

- 输出中文推荐文案。
- 风格接近真实用户的小红书种草笔记。
- 适量 Emoji，分段有留白。
- 输出不少于 80 个中文字符，最多 300 个中文字符。
- 不提 AI、提示词、系统说明。

调优记录：

- 初始版本曾通过 `max_tokens` 控制输出预算，但用户体验上仍然属于 token 限制。
- 当前版本移除生成接口的 `max_tokens` 参数，避免在请求层限制模型输出预算。
- 字数控制全部写入内部 Prompt：Google 为 50-100 个英文字符，小红书为 80-300 个中文字符。
- 后端仍保留空内容防护：非流式接口如果模型第一次返回空正文，会在不传 `max_tokens` 的情况下重试一次；流式接口如果模型没有输出内容，会返回错误事件，不再让前端误判成功。

### 4.1 取消 token 限制的具体改动

本次调整前，生成接口曾通过 `max_tokens` 控制模型输出预算。虽然这种方式可以限制模型生成成本，但它本质上仍然是 token 层面的硬限制，容易带来两个问题：一是用户感知上仍然像“被 token 卡住”，二是部分兼容代理或推理模型可能因为预算策略导致正文为空。

当前版本改为：

- `backend/app/integrations/llm.py` 中的 `OpenAICompatibleClient.complete()` 不再接收 `max_tokens` 参数。
- 发送到模型 `/chat/completions` 的 JSON payload 不再包含 `max_tokens` 字段。
- `backend/app/services/review_service.py` 调用模型时只传 Prompt，不传输出预算。
- `backend/app/core/domain.py` 在 Google 和小红书两套 Prompt 内部写清字数要求。
- 前端提示文案从“减少 token 消耗”改为“通过内部提示词控制字数”。

当前字数规则：

```text
Google 英文评价：不少于 50 个英文字符，最多 100 个英文字符
小红书推荐文案：不少于 80 个中文字符，最多 300 个中文字符
```

需要注意：当前不在后端截断模型输出，也不限制用户最终手动编辑后的发布内容长度。字数要求是生成阶段的 Prompt 约束，最终用户仍可以在文本框中自行增删修改。

### 4.2 流式输出的具体改动

为减少“点击生成后长时间空等”的体验问题，当前前端主流程已切换到流式生成。

后端新增接口：

```text
POST /api/generate-review-stream
```

请求体仍然沿用原来的结构：

```json
{
  "feelings": ["服务好"],
  "platform": "google"
}
```

后端处理流程：

1. `backend/app/api/routes.py` 接收 `/api/generate-review-stream` 请求。
2. 路由层继续走限流、调用日志和成本告警逻辑。
3. `backend/app/services/review_service.py` 组装平台 Prompt，并调用 `llm_client.stream_complete(prompt)`。
4. `backend/app/integrations/llm.py` 向 OpenAI-compatible `/chat/completions` 发送 `stream: true`。
5. 模型返回的 SSE 行中，后端解析 `choices[0].delta.content`。
6. FastAPI 使用 `StreamingResponse` 把片段转换成前端可读的 SSE 事件。

后端返回事件格式：

```text
event: chunk
data: {"text":"模型返回的一段文本"}

event: done
data: {"platform":"google"}
```

如果模型流式调用失败或没有输出内容，后端返回错误事件：

```text
event: error
data: {"message":"错误信息"}
```

前端处理流程：

1. `frontend/src/App.vue` 中点击“生成内容”后，清空旧正文并显示“正在流式生成内容...”。
2. `frontend/src/api.js` 调用 `fetch('/api/generate-review-stream')`。
3. 前端通过 `response.body.getReader()` 读取 `ReadableStream`。
4. `TextDecoder` 将二进制片段转为文本，并按 SSE 的空行分隔事件。
5. 收到 `chunk` 事件时，将 `data.text` 追加到文本框。
6. 收到 `done` 后完成生成，锁定生成按钮，后续只能手动修改。
7. 如果流中断但已经收到部分文本，页面保留当前文本，并提示“生成中断，已保留当前内容，可手动修改”。
8. 如果完全没有收到正文，则显示“模型返回内容为空”或对应的友好错误。

保留兼容接口：

```text
POST /api/generate-review
```

该接口仍返回完整 JSON，用于兼容、调试或后续非流式场景。当前前端主流程不再调用它。

相关代码：

```text
Prompt 与字数限制：backend/app/core/domain.py
生成服务与空内容重试：backend/app/services/review_service.py
模型 HTTP 客户端：backend/app/integrations/llm.py
```

## 5. Webhook 实现说明

任务原计划包含真实企业微信群机器人 Webhook。实际交付中，用户确认不接入真实企业微信，改为通过纯前端代码 mock 演示，重点展示 webhook 的数据拼凑与调用逻辑。

当前 Webhook mock 流程：

1. 用户点击“复制并模拟 Webhook”。
2. 前端复制用户最终正文。
3. 前端根据平台、感受标签和正文生成中文摘要。
4. 前端生成商家回复草稿。
5. 前端拼装企业微信群机器人 Markdown JSON body。
6. 页面展示 mock 请求地址、请求方式、摘要、回复草稿和请求体。

mock 请求地址：

```text
https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=MOCK_DEMO_KEY
```

说明：该地址只用于演示，不会真实发送企业微信群消息，也不需要配置 `WECOM_WEBHOOK_URL`。

## 6. API Key 安全与成本控制

模型 API Key 只放在后端 `backend/.env` 中，不进入前端代码，不进入构建产物。

后端环境变量：

```text
LLM_API_KEY
LLM_BASE_URL
LLM_MODEL
LLM_TIMEOUT_SECONDS
DATABASE_URL
API_RATE_LIMIT_PER_MINUTE
LLM_DAILY_REQUEST_WARNING_LIMIT
API_USAGE_LOG_PATH
FRONTEND_ORIGINS
```

成本控制措施：

- 用户每次流程只允许成功生成一次，生成后只能手动修改。
- 感受标签限制为 1-2 个，减少 Prompt 发散。
- Prompt 严格要求短文本输出，避免模型主动输出长文。
- 后端设置 `LLM_TIMEOUT_SECONDS`，避免模型请求无限等待。
- 后端加入 Demo 级内存限流，默认同一客户端每分钟最多 12 次模型相关请求。
- 后端写入模型调用审计日志，默认路径为 `backend/logs/api-usage.jsonl`，不记录 API Key，不记录评价正文。
- 每日模型请求量达到阈值后写入成本告警日志。

重要说明：当前生成接口不再设置 `max_tokens`，只通过 Prompt 要求短文本输出。用户生成后在文本框里手动修改的最终发布内容不限制长度；如果后续重新公开部署，仍建议接入更强的网关限流、验证码或访问码。

## 7. 数据库说明

本地 Docker PostgreSQL 已预留数据库和表：

```text
容器名：backend-postgres-1
数据库：culture_media
用户：postgres
端口：127.0.0.1:5432
表：culture_media.public.reviews
```

`reviews` 表保存字段包括：

- 平台
- 外部评论 ID
- 顾客昵称
- 评分
- 感受标签
- 评论正文
- 中文摘要
- 商家回复草稿
- 企业微信发送状态
- 创建时间

当前主流程“生成评价 -> 复制 -> mock Webhook -> 跳转平台”不依赖数据库。FastAPI 启动时如果数据库 schema 初始化失败，只写 warning，不阻塞后端启动。数据库只用于后续真实评论来源和入库扩展。

## 8. 本地运行说明

### 8.1 后端

后端运行地址：

```text
http://127.0.0.1:8000
```

后端环境变量示例：

```text
LLM_API_KEY=真实模型 Key
LLM_BASE_URL=真实模型 Base URL
LLM_MODEL=真实模型名称
LLM_TIMEOUT_SECONDS=30
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/culture_media
API_RATE_LIMIT_PER_MINUTE=12
LLM_DAILY_REQUEST_WARNING_LIMIT=100
API_USAGE_LOG_PATH=logs/api-usage.jsonl
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

启动命令：

```powershell
cd "C:\Users\36183\Desktop\boss\culture media\backend"
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

健康检查：

```text
http://127.0.0.1:8000/api/health
```

### 8.2 前端

前端运行地址：

```text
http://127.0.0.1:5173
```

Vite 开发环境已将 `/api` 代理到：

```text
http://127.0.0.1:8000
```

本地生产构建配置：

```text
frontend/.env.production
VITE_API_BASE_URL=http://127.0.0.1:8000
```

启动命令：

```powershell
cd "C:\Users\36183\Desktop\boss\culture media\frontend"
pnpm install
pnpm dev
```

构建命令：

```powershell
cd "C:\Users\36183\Desktop\boss\culture media\frontend"
pnpm build
```

## 9. 测试与验证记录

后端测试命令：

```powershell
cd "C:\Users\36183\Desktop\boss\culture media"
.\backend\.venv\Scripts\python.exe -X utf8 -m unittest discover -s backend\tests -t backend -v
```

最近验证结果：

```text
27 个测试通过
1 个 PostgreSQL 集成测试按配置跳过
```

前端构建命令：

```powershell
cd "C:\Users\36183\Desktop\boss\culture media\frontend"
pnpm build
```

已完成验证：

- 后端健康检查使用 `http://127.0.0.1:8000/api/health`。
- 前端开发服务使用 `http://127.0.0.1:5173`。
- 前端 `/api` 请求通过 Vite proxy 访问本地 FastAPI。
- 真实模型生成已跑通，当前生成接口已取消 `max_tokens` 参数，改为只通过内部 Prompt 控制字数；前端主流程已切换为流式输出。
- 流式生成链路已验证：后端发送 SSE `chunk/done/error` 事件，前端边接收边追加到文本框。
- 生成成功后按钮锁定，只能手动修改。
- 从平台入口后退回页面后，仍可再次点击“打开发布入口”和“复制并模拟 Webhook”。

## 10. 本地启动与依赖导入命令

项目根目录：

```powershell
cd "C:\Users\36183\Desktop\boss\culture media"
```

后端解释器路径：

```text
C:\Users\36183\Desktop\boss\culture media\backend\.venv\Scripts\python.exe
```

后端依赖导入：

```powershell
cd "C:\Users\36183\Desktop\boss\culture media\backend"
uv venv --python 3.11 .venv
.\.venv\Scripts\Activate.ps1
uv pip install --python ".\.venv\Scripts\python.exe" -r requirements.txt
Copy-Item .env.example .env
```

前端依赖导入：

```powershell
cd "C:\Users\36183\Desktop\boss\culture media\frontend"
pnpm install
```

不要使用：

```powershell
uv add --package culture media fastapi
```

原因：`culture media` 是本地文件夹名，不是合法 uv 包名。后端依赖已写在 `backend/requirements.txt` 和 `backend/pyproject.toml`，导入依赖时固定安装到 `backend/.venv`。

## 11. 主要文件路径

```text
项目说明：C:\Users\36183\Desktop\boss\culture media\README.md
交付文档：C:\Users\36183\Desktop\boss\culture media\docs\project-document.md
后端入口：C:\Users\36183\Desktop\boss\culture media\backend\app\main.py
后端路由：C:\Users\36183\Desktop\boss\culture media\backend\app\api\routes.py
Prompt 与字数限制：C:\Users\36183\Desktop\boss\culture media\backend\app\core\domain.py
模型客户端：C:\Users\36183\Desktop\boss\culture media\backend\app\integrations\llm.py
业务服务：C:\Users\36183\Desktop\boss\culture media\backend\app\services\review_service.py
数据库仓库：C:\Users\36183\Desktop\boss\culture media\backend\app\repositories\reviews.py
后端测试：C:\Users\36183\Desktop\boss\culture media\backend\tests
前端页面：C:\Users\36183\Desktop\boss\culture media\frontend\src\App.vue
前端 API：C:\Users\36183\Desktop\boss\culture media\frontend\src\api.js
前端生产配置：C:\Users\36183\Desktop\boss\culture media\frontend\.env.production
```

## 12. 未完成与后续扩展

当前任务书要求的 Demo 主流程已恢复为本地运行。剩余内容属于后续扩展或正式运营增强：

| 类型 | 当前状态 | 后续处理 |
| --- | --- | --- |
| 真实企业微信机器人 | 本次不接入真实机器人，只做前端 mock | 如果后续要真实推送，需要重新启用后端 `WECOM_WEBHOOK_URL` 并调用 `/api/notify-wecom` |
| 真实评论来源 | 已预留 `/api/incoming-review` 和 `reviews` 表，没有接 Google Business Profile API 或小红书真实来源 | 拿到平台授权或第三方评论来源后，把新评论转发到 `/api/incoming-review` |
| 数据库扩展 | 本地 Docker PostgreSQL 已可用；当前主流程不强依赖数据库 | 如需保存评论记录，保持本地 PostgreSQL 可用即可 |
| 成本防护 | 已有 Demo 级限流和调用日志 | 如果后续重新公开部署，建议加验证码、访问码、网关级限流和真实成本告警 |
| 自动化前端测试 | 已做人工浏览器验证和构建验证 | 如长期维护，可补 Playwright/Cypress 自动化用例 |
| PDF 交付 | 已额外导出 PDF | 如果内容继续变化，需要重新导出 PDF |

## 13. 实际耗时

本项目从需求阅读、方案制定、前后端开发、真实模型调试、本地化配置、模型空返回问题排查到文档整理，累计约 4-5 小时。主要耗时集中在真实模型联调、模型返回空正文排查和接口地址配置修复。
