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
