# 求职助手 Agent

自用的求职方向 FastAPI 小项目：前端聊天界面 + 后端 Agent（Function Calling）+ MySQL 岗位库，接入 DeepSeek 大模型做问答。

## 功能

- 岗位查询：按城市、优先级、是否国企筛选在招岗位。
- 面试题生成：按指定方向生成面试题。
- 城市天气：按城市返回当前温度、天气状况、湿度、风速（Open-Meteo 免费接口，无需密钥）。
- 职位卡片直达：页面下方展示岗位卡片，带网页链接的可直接跳转。

## 技术栈

Python · FastAPI · MySQL（SQLAlchemy + PyMySQL）· DeepSeek API（OpenAI 兼容 SDK）· 原生 HTML/CSS/JS 前端

## 目录结构

| 文件 | 职责 |
| --- | --- |
| `main.py` | 后端服务：Agent 问答、岗位列表接口、工具注册与调用分支 |
| `database.py` | 数据库连接与表模型（Job / Question） |
| `config.py` | 读取本地 `.env` 配置（标准库解析，无第三方依赖） |
| `auto_sync_jobs.py` | **岗位巡检脚本**：解析岗位清单 HTML 同步到 MySQL，在招的新增/更新，停止招聘与下架的自动删除，带日志和空数据保护 |
| `import_jobs.example.py` | 岗位初始化导入模板（私人清单复制为 `import_jobs.py` 后使用） |
| `index.html` | 前端聊天 + 职位卡片页面 |
| `test_main.http` | 接口测试用例 |

## 配置

1. 复制 `.env.example` 为 `.env`，填入自己的真实值：

```
DEEPSEEK_API_KEY=你的DeepSeek密钥
DB_USER=root
DB_PASSWORD=你的数据库密码
DB_HOST=localhost
DB_NAME=job_db
JOB_CENTER_DIR=
```

2. `.env` 已被 `.gitignore` 排除，不会上传仓库；密钥和数据库密码不要写进代码。

## 安装与启动

```bash
pip install -r requirements.txt
# 先确保本地 MySQL 已启动，并建好 job_db 库
uvicorn main:app --reload
```

浏览器打开 `http://127.0.0.1:8000`。

## 岗位巡检

`auto_sync_jobs.py` 是离线巡检脚本，手动执行：

```bash
python auto_sync_jobs.py
```

脚本读取 `JOB_CENTER_DIR` 目录下最新一份岗位清单 HTML，同步到 `jobs` 表；数据源缺失、过期或解析不到岗位时跳过本次，不清空数据库。巡检日志写在脚本同目录的 `_sync_jobs_log.txt`。

## 如何巡检其他专业岗位

### 先了解现状

- 本工程默认**不按专业方向过滤**：巡检脚本把数据源 HTML 里解析到的岗位全量入库；后端查询只按城市、优先级、是否国企筛选。
- 岗位方向实际由**数据源清单**决定：巡检读的是 `JOB_CENTER_DIR` 目录下最新一份岗位 HTML，HTML 里有什么就存什么。
- 想换方向，按下面三层改，改动量从小到大。

### 第 1 层：换数据源清单（不改代码，最常用）

1. 把新方向的岗位清单 HTML 放到 `.env` 里 `JOB_CENTER_DIR` 指向的目录。
2. 文件名以「求职中心」开头（脚本按 `求职中心*.html` 匹配最新一份）；要换前缀，同步改 `auto_sync_jobs.py` 里 `_find_center_html` 的 glob。
3. HTML 里岗位沿用 `const jobs = [{...}]` 结构，字段：`co` 公司、`role` 岗位名、`city` 城市、`sal` 薪资、`p` 优先级、`reason` 说明、`url` 链接。
4. 运行 `python auto_sync_jobs.py` 同步到数据库。

### 第 2 层：巡检时按方向过滤（白名单 / 黑名单）

在 `auto_sync_jobs.py` 顶部加关键词，再在解析后过滤，不符合方向的岗位不入库：

```python
# 目标方向关键词（白名单）：岗位名或说明命中任一才保留
INCLUDE_KEYWORDS = ["Python", "测试", "AI", "大模型", "算法", "后端", "RPA"]
# 排除方向关键词（黑名单）：命中任一直接丢弃
EXCLUDE_KEYWORDS = ["Java", "安卓", "前端"]

def _match_direction(job):
    text = (job["position"] + " " + job["description"]).lower()
    if any(k.lower() in text for k in EXCLUDE_KEYWORDS):
        return False
    return any(k.lower() in text for k in INCLUDE_KEYWORDS)
```

在 `sync_jobs()` 里 `jobs = parse_jobs(html_text)` 之后加一行：

```python
jobs = [j for j in jobs if _match_direction(j)]
```

> 白名单是「命中才留」。如果只想排除个别方向、其余都留，就把 `INCLUDE_KEYWORDS` 留空、只配黑名单。

### 第 3 层：后端查询和 Agent 提示词配合

- `search_jobs`（`main.py`）可再加一个关键词参数，按岗位名或说明过滤。需要先从 `sqlalchemy` 导入 `or_`：

```python
if keyword:
    query = query.filter(or_(Job.position.like(f"%{keyword}%"),
                             Job.description.like(f"%{keyword}%")))
```

- Agent 想固定只聊目标方向，可在 `/api/agent` 的 `messages` 最前面加一条 `system` 消息，写明目标方向和排除方向（当前代码只有 user 消息）。

### 改完生效

- 巡检脚本是离线手动跑，改完直接 `python auto_sync_jobs.py`。
- 后端代码（`main.py`）改完要重启 uvicorn 才生效。
