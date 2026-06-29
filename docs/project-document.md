# AI 评价生成 Demo 项目文档

## 1. AI 辅助编程工具使用策略

本项目使用 Codex 进行需求拆解、架构规划、测试优先的后端实现、前端移动端界面搭建和交付文档整理。当前演示策略调整为“真实模型生成 + 前端 Webhook mock”：评价生成允许接入真实大模型，企业微信机器人不做真实接入，只在前端展示 Webhook 数据拼凑与模拟调用逻辑。

AI 主要用于：

- 从需求文档中提取用户流程、接口边界和评分重点。
- 生成后端业务测试，先验证 1-2 个感受限制、平台限制、Prompt 选择和历史 Webhook 路径。
- 协助编写 Vue 移动端界面和状态反馈，避免空白失败和不可恢复状态。
- 整理 API Key 安全、Prompt 调优、Webhook mock 演示和部署说明。

人工判断主要用于：

- 确认技术路线为 Vue/Vite 前端 + Python FastAPI 后端。
- 确认真实模型调用可以接入，真实企业微信群机器人 Webhook 当前不接入，改为前端 mock 演示。
- 将 PinMe 限定为 Vue/Vite 静态前端部署候选，Python 后端部署后续单独确认。

## 2. Prompt 设计思路与调优过程

后端将平台拆成两套 Prompt，避免同一个 Prompt 同时兼容英文 Google 评论和中文小红书笔记导致风格折中。

Google Prompt 的设计目标：

- 英文输出。
- 使用北美本地真实消费者口吻。
- 语气客观、具体、温和。
- AI 生成阶段控制在约 45-75 个英文词，并通过 `max_tokens` 控制输出长度和 token 消耗。
- 避免过度营销、优惠引导、AI 痕迹和任务说明。

小红书 Prompt 的设计目标：

- 中文输出。
- 输出推荐文案，符合“种草笔记”语感。
- 适量使用 Emoji。
- 段落有留白和呼吸感。
- AI 生成阶段控制在约 80-140 个中文字符，并通过 `max_tokens` 控制输出长度和 token 消耗。
- 像真实用户分享，而不是商家广告。

历史后端预留的 Webhook 分析 Prompt 单独设计，不复用评价生成 Prompt。它要求模型严格返回两行：

```text
中文摘要：用一句中文概括顾客主要反馈
商家回复草稿：用一句亲切、专业、不夸张的中文回复顾客
```

这样后端可以用确定性解析逻辑提取摘要与回复草稿，避免再用模型做路由或状态判断。当前交付的企业微信演示不调用真实后端 Webhook，只在前端 mock 中生成摘要、回复草稿和请求体。

## 3. 自动化工作流与 Webhook

当前交付版本中，顾客点击“生成内容”时，前端会请求后端 `/api/generate-review`，由 FastAPI 使用 `LLM_API_KEY`、`LLM_BASE_URL` 和 `LLM_MODEL` 调用真实模型。Google 生成英文评价，小红书生成推荐文案；生成阶段会通过 Prompt 和 `max_tokens` 控制输出长度，用来减少 token 消耗。这个限制只作用于 AI 生成内容，不限制用户生成后手动修改的最终发布内容长度。生成成功后不能再次生成，只能在文本框中手动修改。顾客点击“复制并模拟 Webhook”后，前端先复制最终正文。复制成功后在纯前端执行 mock 调用逻辑：

1. 前端根据评价正文、平台和感受标签生成中文摘要。
2. 前端生成商家回复草稿。
3. 前端按企业微信群机器人 Markdown 消息格式拼装 JSON body。
4. 前端展示 mock 请求地址、请求方式、请求 body 和 mock 调用状态。
5. 用户可单独点击“打开发布入口”跳转到 Google 或小红书入口。

当前版本不发送真实企业微信消息，不需要 `WECOM_WEBHOOK_URL`。页面展示的是如果接入真实企微机器人时应该发送的 payload。真实模型生成需要后端服务；企业微信 Webhook 演示不需要后端参与。

此前实现的后端 `/api/incoming-review` 和 PostgreSQL `reviews` 表保留为后续真实接入基础，但不作为当前演示的必需运行条件。

## 4. API Key 安全与用量成本处理

当前版本允许接入真实模型，因此需要在后端配置模型 API Key。前端不保存模型 API Key，只通过 `/api/generate-review` 调用 FastAPI 后端；后端通过环境变量读取：

- `LLM_API_KEY`
- `LLM_BASE_URL`
- `LLM_MODEL`
- `LLM_TIMEOUT_SECONDS`
- `DATABASE_URL`
- `API_RATE_LIMIT_PER_MINUTE`
- `LLM_DAILY_REQUEST_WARNING_LIMIT`
- `API_USAGE_LOG_PATH`
- `FRONTEND_ORIGINS`

当前版本不接入真实企业微信机器人，因此不需要配置 `WECOM_WEBHOOK_URL`。

成本控制方式：

- 每次流程只允许成功生成一次，不做多候选生成；后续修改必须由用户手动编辑。
- Google 和小红书的生成接口分别传入短输出 `max_tokens`，只限制 AI 输出长度，不限制用户最终发布内容长度。
- 感受标签限制为 1-2 个，减少 Prompt 发散。
- Webhook 摘要与回复草稿由前端 mock 生成，不产生企业微信外部调用成本。
- 后端保留 `LLM_TIMEOUT_SECONDS`，避免请求无限等待。
- 后端已增加 Demo 级内存限流，默认同一客户端每分钟最多 12 次模型相关请求，超过后返回 429。
- 后端已增加模型调用审计日志，默认写入 `backend/logs/api-usage.jsonl`，记录接口、平台、感受数量、匿名客户端哈希、状态码和告警事件，不记录 API Key 或评价正文。
- 后端已增加每日模型请求量告警阈值，默认达到 100 次后写入 `model_cost_warning` 日志，并输出后端 warning。
- 后续正式上线时仍建议增加网关级限流、验证码或一次性短码、持久化监控和真实成本通知，减少公开 Demo 被刷量风险。

## 5. 实际耗时

本轮 Codex 实作记录约 2 小时，包括需求阅读、计划确认、后端测试与实现、前端页面搭建、文档整理和本地验证。若后续继续配置真实模型 Key、部署后端、生成正式 PDF 文档，请在最终提交前按实际追加耗时更新。

## 6. 部署说明

前端是 Vue/Vite，构建产物为 `frontend/dist/`，可用于 PinMe 静态上传。没有自有域名时，直接使用 PinMe 生成的访问链接即可。

本地开发时，Vite 已经把 `/api` 代理到 `http://127.0.0.1:8000`。如果前端和后端分开部署，Python FastAPI 后端需要单独部署到支持 Python 常驻服务的平台，并配置模型环境变量；前端生产环境再通过 `VITE_API_BASE_URL` 指向该后端。

推荐发布方式：

```text
前端：PinMe 静态上传 frontend/dist/
后端：Render、Railway 或其他 Python Web Service 平台
数据库：后端平台托管 PostgreSQL，或其他公网 PostgreSQL
```

后端平台配置：

```text
Root Directory: backend
Python Version: 3.11
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

后端线上环境变量：

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

`FRONTEND_ORIGINS` 填前端访问链接的 origin。比如 PinMe 预览链接是 `https://pinme.eth.limo/#/preview/xxx`，这里填 `https://pinme.eth.limo`；如果误填完整链接，后端也会自动取 origin。

前端生产环境配置：复制 `frontend/.env.production.example` 为 `frontend/.env.production`，并填写后端平台地址。

```text
VITE_API_BASE_URL=https://你的后端平台地址
```

本阶段不强行把 Python 后端放入 PinMe 全栈路径，因为当前 PinMe 全栈模板更偏 React/Vite + Worker 后端；为避免部署方案失真，前后端部署先解耦。

## 7. 未完成功能与待补充内容

当前 Demo 的前后端主流程、接口结构、后端单元测试、前端本地构建和无 Key 状态下的页面验证已经完成。下面这些事项还没有最终完成，主要原因是需要真实模型配置、正式部署环境或最终交付要求确认。

| 类型 | 未完成项 | 当前状态 | 后续处理 |
| --- | --- | --- | --- |
| 真实模型调用 | 接入可用的 `LLM_API_KEY` 并完成真实生成验证 | 当前已经允许接入真实模型，前端会调用后端 `/api/generate-review` | 在 `backend/.env` 填入真实 `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL` 后，用手机视口重新验证 |
| 企微推送 | 使用真实企业微信群机器人 Webhook 验证消息到群 | 当前不作为交付目标，不接入真实企业微信机器人；只展示 Webhook payload 拼装和 mock 调用结果 | 保持前端 mock 演示即可，不配置 `WECOM_WEBHOOK_URL` |
| 真实评论来源 | 自动收到 Google/小红书的新评论 | 后端已提供 `/api/incoming-review` 接收入口和入库基础；还没有接 Google Business Profile API 或小红书实际来源 | 后续拿到平台授权或第三方评论来源后，把新评论转发到 `/api/incoming-review` |
| 生产部署 | 前端和后端正式上线 | 前端 `frontend/dist/` 可作为 PinMe 静态上传目标；后端支持通过 `FRONTEND_ORIGINS` 放行平台自带前端域名 | 选择 Render、Fly、Railway、云函数或其他 Python 服务平台，配置环境变量，再给前端设置 `VITE_API_BASE_URL` |
| 平台入口 | 替换成真实、最准确的商家发布入口 | Google 当前打开 Sunny Tea House San Jose 的 Google Maps/Search 入口；小红书当前打开网页入口，不做内容预填 | 拿到 Google 商家评论链接或 Place ID 后替换；如有小红书官方账号或可识别 App 链接，也可替换当前入口 |
| 正式端到端验收 | 使用真实模型 Key、手机视口完成完整闭环截图 | 已完成本地无 Key 友好错误、手动编辑、按钮状态和构建验证；真实模型调用未验收 | 配置真实模型环境变量后，按“选择感受 -> 生成 -> 编辑 -> 复制并模拟 Webhook -> 平台跳转”重新截图验收 |
| 上线安全 | 公开 Demo 的滥用防护和日志监控 | 已补 Demo 级内存限流、调用日志和每日请求量告警；还没有登录、验证码、网关级限流或外部告警通知 | 上线前增加网关级限流、验证码、持久化监控和真实成本通知，避免公开链接被刷模型调用 |
| 前端自动化测试 | 前端端到端自动化测试脚本 | 已做浏览器人工验证和 Vite 构建，尚未补 Playwright/Cypress 自动化用例 | 如需要长期维护，补充移动端 375px 视口下的生成失败、复制成功、推送失败、平台切换用例 |
| 正式交付 PDF | 将 Markdown 交付文档导出为 PDF | 当前交付文档是 Markdown 格式，尚未导出 PDF | 若老师或交付方要求 PDF，需要按字体规则导出并检查字体、字号和空行 |

后续真实接入优先级建议：

1. 先配置真实 `LLM_API_KEY`、`LLM_BASE_URL` 和 `LLM_MODEL`，验证后端可以生成 Google 与小红书两种风格。
2. 再确定后端部署平台，并把前端生产环境的 `VITE_API_BASE_URL` 指向线上后端。
3. 企业微信保持前端 mock，不进入当前交付范围。

## 8. 本地启动与依赖导入命令

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
后端数据库测试：C:\Users\36183\Desktop\boss\culture media\backend\tests\test_postgres_repository.py
```

后端启动：

```powershell
cd "C:\Users\36183\Desktop\boss\culture media\backend"
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

前端依赖导入与启动：

```powershell
cd "C:\Users\36183\Desktop\boss\culture media\frontend"
pnpm install
pnpm dev
```

前端常用文件路径：

```text
前端依赖配置：C:\Users\36183\Desktop\boss\culture media\frontend\package.json
前端 Vite 配置：C:\Users\36183\Desktop\boss\culture media\frontend\vite.config.js
前端页面入口：C:\Users\36183\Desktop\boss\culture media\frontend\src\App.vue
前端 API 封装：C:\Users\36183\Desktop\boss\culture media\frontend\src\api.js
前端样式文件：C:\Users\36183\Desktop\boss\culture media\frontend\src\styles.css
```

本地访问地址：

```text
后端健康检查：http://127.0.0.1:8000/api/health
前端页面：http://127.0.0.1:5173
```

不要使用 `uv add --package culture media fastapi`。`culture media` 是本地文件夹名，不是合法的 uv 包名；后端依赖记录在 `backend/requirements.txt` 和 `backend/pyproject.toml`，安装时要显式指定 `backend/.venv` 的 Python。

也不要在本项目根目录执行普通 `uv sync`，它可能会按 workspace 规则创建根目录 `.venv`。本项目后端解释器固定使用 `backend/.venv`，依赖导入请使用：

```powershell
cd "C:\Users\36183\Desktop\boss\culture media\backend"
uv pip install --python ".\.venv\Scripts\python.exe" -r requirements.txt
```

## 9. PostgreSQL 评论表与新评论接口

当前使用 Docker 中已经运行的 PostgreSQL：

```text
容器名：backend-postgres-1
镜像：pgvector/pgvector:pg16
数据库：culture_media
用户：postgres
密码：postgres
端口：127.0.0.1:5432
连接串：postgresql://postgres:postgres@127.0.0.1:5432/culture_media
```

后端启动时会自动在 `culture_media.public` 下创建 `reviews` 表。表中保存：

- `source`：来源，`generated` 表示前端生成评价后复制触发，`incoming` 表示外部新评论接入。
- `platform`：平台，当前支持 `google` 和 `xiaohongshu`。
- `external_review_id`：平台或外部系统传来的评论 ID。
- `author`：顾客昵称。
- `rating`：评分。
- `feelings`：感受标签，JSON 数组。
- `review_text`：原始评论正文。
- `summary`：中文摘要。
- `reply_draft`：商家回复草稿。
- `wecom_sent`：历史字段；当前不配置真实企业微信机器人时为 `false`。
- `created_at`：入库时间。

新评论接口：

```text
POST /api/incoming-review
```

请求示例：

```json
{
  "platform": "google",
  "reviewId": "google-review-001",
  "author": "Alice",
  "rating": 5,
  "review": "Milk tea tasted great and the team was friendly.",
  "feelings": []
}
```

响应示例：

```json
{
  "id": 3,
  "sent": false,
  "summary": "顾客喜欢饮品和服务。",
  "replyDraft": "感谢您的支持，欢迎下次再来。"
}
```

查看最近入库记录：

```powershell
docker exec backend-postgres-1 psql -U postgres -d culture_media -c "SELECT id, source, platform, external_review_id, author, rating, summary, wecom_sent, created_at FROM reviews ORDER BY id DESC LIMIT 5;"
```

## 10. 文档文件路径

```text
项目说明：C:\Users\36183\Desktop\boss\culture media\README.md
交付文档草稿：C:\Users\36183\Desktop\boss\culture media\docs\project-document.md
原始需求 PDF：C:\Users\36183\Desktop\boss\culture media\AI评价生成Demo(2)(2)(1)(1)(1).pdf
```
