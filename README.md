# Sunny Tea House AI 评价生成 Demo

一个本地运行的移动端 H5 Demo：顾客选择 1-2 个消费感受和发布平台后，后端调用真实大模型生成评价，用户可编辑、一键复制，并在页面内展示企业微信 Webhook 的请求地址、请求方式和 JSON body 拼装结果。

当前交付模式是“真实模型生成 + 前端 Webhook mock”：允许接入真实模型，但不接入真实企业微信机器人。模型密钥只放在后端环境变量中；企业微信部分只在前端演示数据拼装与模拟调用结果，不需要配置真实 `WECOM_WEBHOOK_URL`。

AI 生成长度控制：后端不再给生成请求设置 `max_tokens`，只通过内部 Prompt 限制模型输出字数。Google 英文评价要求不少于 50 个英文字符、最多 100 个英文字符；小红书推荐文案要求不少于 80 个中文字符、最多 300 个中文字符。用户生成后在文本框里手动修改的最终发布内容不限制长度。每次进入流程只允许成功生成一次，生成后按钮会锁定，后续只能在文本框中手动修改。

最近两项生成体验改动：

1. 取消 token 输出预算限制：模型请求体不再发送 `max_tokens`，避免请求层再次限制生成长度。字数约束只写在后端内部 Prompt 中，由模型按平台输出对应长度；前端仅展示当前正文长度，不限制用户手动修改后的最终内容。
2. 增加流式输出：前端主流程改为调用 `/api/generate-review-stream`。后端请求模型时使用 OpenAI-compatible `stream: true`，把模型返回的 `delta.content` 转成 SSE 事件；前端用 `ReadableStream` 边读边把文本追加到编辑框，用户不需要等完整响应结束才看到正文。

本地访问地址：

```text
前端：http://127.0.0.1:5173
后端：http://127.0.0.1:8000
健康检查：http://127.0.0.1:8000/api/health
```

## 项目结构

```text
backend/
  app/
    api/           FastAPI 路由和请求模型
    core/          配置、平台常量、校验规则、Prompt 和消息格式
    integrations/  大模型外部调用与历史预留客户端
    repositories/  PostgreSQL 评论表建表与写入
    services/      评价生成和历史预留业务流程
    main.py        应用装配与跨域配置
  tests/           后端单元测试
frontend/          Vue 3 + Vite 移动端 H5
docs/              交付文档草稿
```

## 后端依赖导入与启动

先进入项目根目录：

```powershell
cd "C:\Users\36183\Desktop\boss\culture media"
```

进入后端目录：

```powershell
cd "C:\Users\36183\Desktop\boss\culture media\backend"
uv venv --python 3.11 .venv
.\.venv\Scripts\Activate.ps1
uv pip install --python ".\.venv\Scripts\python.exe" -r requirements.txt
Copy-Item .env.example .env
```

PyCharm 解释器请选择：

```text
C:\Users\36183\Desktop\boss\culture media\backend\.venv\Scripts\python.exe
```

不要使用下面这种命令：

```powershell
uv add --package culture media fastapi
```

`culture media` 是本地目录名，不是合法的 uv 包名。后端依赖已经写在 `backend/requirements.txt` 和 `backend/pyproject.toml`，导入依赖请使用上面的 `uv pip install --python ".\.venv\Scripts\python.exe" -r requirements.txt`，这样依赖会进入 `backend/.venv`。

后端常用文件路径：

```text
后端依赖配置：C:\Users\36183\Desktop\boss\culture media\backend\pyproject.toml
后端环境变量：C:\Users\36183\Desktop\boss\culture media\backend\.env
后端环境变量示例：C:\Users\36183\Desktop\boss\culture media\backend\.env.example
后端应用入口：C:\Users\36183\Desktop\boss\culture media\backend\app\main.py
后端接口路由：C:\Users\36183\Desktop\boss\culture media\backend\app\api\routes.py
后端 Prompt 与校验：C:\Users\36183\Desktop\boss\culture media\backend\app\core\domain.py
后端数据库仓库：C:\Users\36183\Desktop\boss\culture media\backend\app\repositories\reviews.py
后端测试文件：C:\Users\36183\Desktop\boss\culture media\backend\tests\test_review_flow.py
```

编辑 `backend/.env`：

```text
LLM_API_KEY=replace-with-provider-key
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_MODEL=deepseek-chat
LLM_TIMEOUT_SECONDS=30
DATABASE_URL=postgresql://postgres:postgres@127.0.0.1:5432/culture_media
API_RATE_LIMIT_PER_MINUTE=12
LLM_DAILY_REQUEST_WARNING_LIMIT=100
API_USAGE_LOG_PATH=logs/api-usage.jsonl
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

当前版本不接入真实企业微信机器人，`backend/.env` 不需要填写 `WECOM_WEBHOOK_URL`。

公开 Demo 保护说明：

- `API_RATE_LIMIT_PER_MINUTE`：同一客户端每分钟最多允许多少次模型相关请求，超过后返回 429。
- `LLM_DAILY_REQUEST_WARNING_LIMIT`：当日模型请求数达到该值后，后端写入成本告警日志。
- `API_USAGE_LOG_PATH`：模型调用审计日志路径，默认写入 `backend/logs/api-usage.jsonl`；日志不记录 API Key，也不记录评价正文。

启动：

```powershell
cd "C:\Users\36183\Desktop\boss\culture media\backend"
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

后端启动后访问：

```text
http://127.0.0.1:8000/api/health
```

## 前端依赖导入与启动

进入前端目录：

```powershell
cd "C:\Users\36183\Desktop\boss\culture media\frontend"
pnpm install
pnpm dev
```

前端启动后访问：

```text
http://127.0.0.1:5173
```

前端生成内容会通过 Vite 代理调用后端 `/api/generate-review-stream`，模型文本会以流式片段实时追加到文本框。完整生成流程需要先启动后端，并在 `backend/.env` 中配置可用的 `LLM_API_KEY`、`LLM_BASE_URL` 和 `LLM_MODEL`。如果没有配置模型 Key，页面会显示可重试的中文错误提示；如果流式生成中断但已经收到部分文本，页面会保留当前内容并提示可手动修改。复制后的企业微信 Webhook 展示仍由前端 mock 完成。生成成功后不能再次生成，只能手动修改文本框内容。旧的 `/api/generate-review` 非流式接口保留用于兼容和调试。

前端常用文件路径：

```text
前端依赖配置：C:\Users\36183\Desktop\boss\culture media\frontend\package.json
前端 Vite 配置：C:\Users\36183\Desktop\boss\culture media\frontend\vite.config.js
前端页面入口：C:\Users\36183\Desktop\boss\culture media\frontend\src\App.vue
前端 API 封装：C:\Users\36183\Desktop\boss\culture media\frontend\src\api.js
前端样式文件：C:\Users\36183\Desktop\boss\culture media\frontend\src\styles.css
```

本地开发时，Vite 已经把 `/api` 代理到 `http://127.0.0.1:8000`。如果需要本地构建后预览，也可以复制 `frontend/.env.production.example` 为 `frontend/.env.production`，保持后端地址为本机回环地址：

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## 测试

当前后端核心逻辑使用 Python 标准库 `unittest`，无需额外测试依赖：

```powershell
backend\.venv\Scripts\python.exe -X utf8 -m unittest discover -s backend\tests -t backend -v
```

如果要验证 Docker PostgreSQL 建表和插入：

```powershell
$env:RUN_POSTGRES_TESTS='1'
backend\.venv\Scripts\python.exe -X utf8 -m unittest discover -s backend\tests -t backend -p test_postgres_repository.py -v
```

前端安装依赖后可运行：

```powershell
cd frontend
pnpm build
```

## 本地回环访问说明

当前已解除 Render 后端和 PinMe 前端部署，项目恢复为本机运行方式：

```text
前端：http://127.0.0.1:5173
后端：http://127.0.0.1:8000
前端调用后端：开发环境通过 Vite proxy 转发 /api 到 http://127.0.0.1:8000
数据库：本地 Docker PostgreSQL，地址为 127.0.0.1:5432
```

后端 CORS 只需要允许本地前端：

```text
FRONTEND_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
```

本地生产构建配置：

```text
frontend/.env.production
VITE_API_BASE_URL=http://127.0.0.1:8000
```

本地构建检查：

```powershell
cd "C:\Users\36183\Desktop\boss\culture media\frontend"
pnpm build
```

当前交付不配置真实企业微信 Webhook。

## 数据库与新评论接口

下面内容是后续接真实评论来源时的预留能力。当前演示主流程只需要真实模型生成，不依赖数据库，也不接入真实企业微信机器人。

当前后端会连接 Docker 中的 PostgreSQL：

```text
容器名：backend-postgres-1
数据库：culture_media
用户：postgres
密码：postgres
本机端口：5432
连接串：postgresql://postgres:postgres@127.0.0.1:5432/culture_media
```

FastAPI 启动时会自动创建一张表：

```text
reviews
```

这张表保存平台、外部评论 ID、顾客昵称、评分、感受标签、评论正文、中文摘要、商家回复草稿、企微是否发送、创建时间。

注意：项目评论数据现在单独放在 `culture_media.public.reviews`，不再写入 `ai_portfolio.public.reviews`。

现在保留两条后端入库路径，作为后续扩展基础；当前前端主流程不会调用它们：

- `/api/notify-wecom`：历史预留接口，可保存用户最终复制的评价；当前前端已改为本地 mock，不再调用该接口。
- `/api/incoming-review`：后续真实评论来源使用，只要外部系统把新评论 POST 过来，后端就会生成摘要和回复草稿，并写入 `reviews` 表。

新评论接口示例：

```powershell
Invoke-RestMethod `
  -Method Post `
  -Uri "http://127.0.0.1:8000/api/incoming-review" `
  -ContentType "application/json; charset=utf-8" `
  -Body (@{
    platform = "google"
    reviewId = "google-review-001"
    author = "Alice"
    rating = 5
    review = "Milk tea tasted great and the team was friendly."
    feelings = @()
  } | ConvertTo-Json -Depth 5)
```

查看最近入库记录：

```powershell
docker exec backend-postgres-1 psql -U postgres -d culture_media -c "SELECT id, source, platform, external_review_id, author, rating, summary, wecom_sent, created_at FROM reviews ORDER BY id DESC LIMIT 5;"
```

## 未完成事项

当前 Demo 主流程已恢复为本地运行，剩余内容主要是后续扩展或正式运营增强：

- 真实企微推送：当前不作为交付目标，不接入真实企业微信机器人；前端只展示 Webhook payload 拼装和 mock 调用结果。
- 真实评论来源：后端已有 `/api/incoming-review` 接口，但还没有接 Google Business Profile API、小红书或其他真实评论来源。
- 数据库扩展：本地 Docker PostgreSQL 已预留 `culture_media.public.reviews` 表；当前主流程不强依赖数据库。
- 平台入口：Google 当前使用搜索/地图入口，小红书当前使用网页入口；如拿到更准确的商家评论链接、Place ID 或小红书 App 链接，需要再替换。
- 安全与成本：已补基础内存限流、调用日志和每日请求量告警；如果后续重新公开部署，仍建议接入网关级限流、持久化监控和成本告警通知。
- 正式交付 PDF：当前交付文档是 Markdown，若最终要求 PDF，需要再按字体规则导出并检查版式。

详细清单见：

```text
C:\Users\36183\Desktop\boss\culture media\docs\project-document.md
```

## 文档文件路径

```text
项目说明：C:\Users\36183\Desktop\boss\culture media\README.md
交付文档草稿：C:\Users\36183\Desktop\boss\culture media\docs\project-document.md
原始需求 PDF：C:\Users\36183\Desktop\boss\culture media\AI评价生成Demo(2)(2)(1)(1)(1).pdf
```
