# Sunny Tea House AI 评价生成 Demo

一个移动端 H5 Demo：顾客选择 1-2 个消费感受和发布平台后，后端调用真实大模型生成评价，用户可编辑、一键复制，并在页面内展示企业微信 Webhook 的请求地址、请求方式和 JSON body 拼装结果。

当前交付模式是“真实模型生成 + 前端 Webhook mock”：允许接入真实模型，但不接入真实企业微信机器人。模型密钥只放在后端环境变量中；企业微信部分只在前端演示数据拼装与模拟调用结果，不需要配置真实 `WECOM_WEBHOOK_URL`。

AI 生成长度控制：Google 生成英文评价时会通过 Prompt 和 `max_tokens` 控制在约 45-75 个英文词；小红书生成推荐文案时会控制在约 80-140 个中文字符。这个限制只用于减少模型输出和 token 消耗，不限制用户生成后在文本框里手动修改的最终发布内容长度。每次进入流程只允许成功生成一次，生成后按钮会锁定，后续只能在文本框中手动修改。

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

前端生成内容会通过 Vite 代理调用后端 `/api/generate-review`，完整生成流程需要先启动后端，并在 `backend/.env` 中配置可用的 `LLM_API_KEY`、`LLM_BASE_URL` 和 `LLM_MODEL`。如果没有配置模型 Key，页面会显示可重试的中文错误提示；复制后的企业微信 Webhook 展示仍由前端 mock 完成。生成成功后不能再次生成，只能手动修改文本框内容。

前端常用文件路径：

```text
前端依赖配置：C:\Users\36183\Desktop\boss\culture media\frontend\package.json
前端 Vite 配置：C:\Users\36183\Desktop\boss\culture media\frontend\vite.config.js
前端页面入口：C:\Users\36183\Desktop\boss\culture media\frontend\src\App.vue
前端 API 封装：C:\Users\36183\Desktop\boss\culture media\frontend\src\api.js
前端样式文件：C:\Users\36183\Desktop\boss\culture media\frontend\src\styles.css
```

本地开发时，Vite 已经把 `/api` 代理到 `http://127.0.0.1:8000`。如果前端和后端分开部署，复制 `frontend/.env.production.example` 为 `frontend/.env.production`，再填线上后端地址：

```text
VITE_API_BASE_URL=https://your-python-backend.example.com
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

## 发布方案

没有自有域名也可以发布。推荐保持当前前后端分离结构：

```text
前端：PinMe 静态上传 frontend/dist/
后端：Render、Railway 或其他 Python Web Service 平台
数据库：后端平台托管 PostgreSQL，或其他公网 PostgreSQL
```

先发布后端，使用平台自动生成的公开地址即可，例如 `https://your-backend.onrender.com` 或 Railway 生成的域名。后端平台配置：

```text
Root Directory: backend
Python Version: 3.11
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

后端线上环境变量至少填写：

```text
LLM_API_KEY=真实模型key
LLM_BASE_URL=模型base_url
LLM_MODEL=模型名
LLM_TIMEOUT_SECONDS=30
DATABASE_URL=线上PostgreSQL连接串
API_RATE_LIMIT_PER_MINUTE=12
LLM_DAILY_REQUEST_WARNING_LIMIT=100
API_USAGE_LOG_PATH=logs/api-usage.jsonl
FRONTEND_ORIGINS=https://pinme.eth.limo
```

`FRONTEND_ORIGINS` 填前端访问链接的 origin。比如 PinMe 预览链接是 `https://pinme.eth.limo/#/preview/xxx`，这里填 `https://pinme.eth.limo` 即可；如果不确定，也可以先粘完整链接，后端会自动取 origin。

后端发布后先访问：

```text
https://你的后端平台地址/api/health
```

再配置前端生产环境。复制 `frontend/.env.production.example` 为 `frontend/.env.production`，并填写后端平台地址：

```text
VITE_API_BASE_URL=https://你的后端平台地址
```

Vue/Vite 前端构建产物位于 `frontend/dist/`，可作为 PinMe 静态上传目标：

```powershell
cd frontend
pnpm build
pinme upload dist
```

PinMe 会输出一个可访问链接，直接用这个链接演示即可，不需要购买域名。当前交付不配置真实企业微信 Webhook。

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

当前本地 Demo 主流程已改为真实模型生成、前端 mock 企业微信 Webhook，剩余未完成内容主要集中在真实外部配置、正式上线和最终交付验收：

- 真实模型调用验证：已允许接入真实模型；需要在 `backend/.env` 配置可用的 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` 后，用真实账号完成一次生成验收。
- 真实企微推送：当前不作为交付目标，不接入真实企业微信机器人；前端只展示 Webhook payload 拼装和 mock 调用结果。
- 真实评论来源：后端已有 `/api/incoming-review` 接口，但还没有接 Google Business Profile API、小红书或其他真实评论来源。
- 生产部署：前端可构建为 `frontend/dist/`，后端还需要确认 Render、Fly、Railway、云函数等 Python 服务部署方案。
- 平台入口：Google 当前使用搜索/地图入口，小红书当前使用网页入口；如拿到更准确的商家评论链接、Place ID 或小红书 App 链接，需要再替换。
- 正式验收截图：真实模型 Key 配好后，需要重新完成“选择感受 -> 生成 -> 编辑 -> 复制并模拟 Webhook -> 平台跳转”的完整闭环截图。
- 上线安全：已补基础内存限流、调用日志和每日请求量告警；正式公开前仍建议接入网关级限流、持久化监控和成本告警通知。
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
