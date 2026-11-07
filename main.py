# 导入FastAPI
from fastapi import FastAPI, Depends
from fastapi.responses import FileResponse
# 导入BaseModel，用来定义前端发过来的数据格式
from pydantic import BaseModel

# 导入Session类型，用来标注数据库连接
from sqlalchemy.orm import Session

# 导入date，用来获取今天的日期
from datetime import date

# 导入OpenAI库，DeepSeek兼容OpenAI的接口
from openai import OpenAI

# 导入json，用来解析大模型返回的参数
import json

# 读取本地配置（密钥等从环境变量或 .env 取，不在代码里写死）
from config import get

# 从我们自己写的database.py里导入需要的东西
from database import engine, SessionLocal, Base, Question, Job

# 创建FastAPI应用
app = FastAPI()


# ========== 数据库连接函数 ==========
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ========== GET接口：岗位列表（供前端直达职位网页） ==========
@app.get("/api/jobs")
def get_jobs(db: Session = Depends(get_db)):
    jobs = db.query(Job).all()
    result = []
    for j in jobs:
        result.append({
            "company": j.company,
            "position": j.position,
            "city": j.city,
            "salary": j.salary,
            "priority": j.priority,
            "job_type": j.job_type,
            "is_soe": bool(j.is_soe),
            "url": j.url or "",
            "description": j.description or ""
        })
    return result


# ========== 初始化DeepSeek客户端 ==========
# 密钥从环境变量或本地 .env 读取，不在代码里写死；模板见 .env.example
_deepseek_key = get("DEEPSEEK_API_KEY", "")
if not _deepseek_key:
    raise RuntimeError("缺少 DEEPSEEK_API_KEY，请在 .env 或环境变量里配置（参考 .env.example）")

client = OpenAI(
    api_key=_deepseek_key,
    base_url=get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
)


# ========== Day3：简单聊天接口 ==========
@app.post("/api/chat")
def chat(message: str):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": message}
        ]
    )
    return {"reply": response.choices[0].message.content}


# ========== 工具1：生成面试题 ==========
def generate_questions(category: str, count: int = 5):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "user", "content": f"给我{count}道{category}的面试题，带答案，标明来源"}
        ]
    )
    return response.choices[0].message.content


# ========== 工具3：搜索岗位 ==========
def search_jobs(city: str = "", priority: str = "", is_soe: bool = False):
    db = SessionLocal()
    query = db.query(Job)
    
    if city:
        query = query.filter(Job.city.like(f"%{city}%"))
    if priority:
        query = query.filter(Job.priority == priority)
    if is_soe:
        query = query.filter(Job.is_soe == True)
    
    jobs = query.all()
    db.close()

    if not jobs:
        return "没找到符合条件的岗位"
    
    result = []
    for j in jobs:
        soe_tag = "【国企】" if j.is_soe else ""
        result.append(f"{soe_tag}{j.company} - {j.position} | {j.city} | {j.salary} | {j.priority}")
    
    return f"找到{len(jobs)}个岗位：\n" + "\n".join(result)


# ========== 工具4：查询城市天气 ==========
def _weather_text(code):
    table = {
        0: "晴", 1: "大致晴朗", 2: "局部多云", 3: "阴",
        45: "雾", 48: "雾凇",
        51: "轻毛毛雨", 53: "毛毛雨", 55: "浓毛毛雨",
        61: "小雨", 63: "中雨", 65: "大雨",
        71: "小雪", 73: "中雪", 75: "大雪",
        80: "小阵雨", 81: "阵雨", 82: "强阵雨",
        95: "雷阵雨", 96: "雷阵雨伴冰雹", 99: "强雷阵雨伴冰雹",
    }
    return table.get(code, "未知")


def get_weather(city: str = ""):
    import urllib.request
    import urllib.parse

    if not city:
        return "请告诉我要查哪个城市"
    # 城市名可能带区县（如 成都·武侯），取第一个地名
    city_name = city.replace("·", " ").split()[0]

    try:
        # 1) 地理编码：城市名 -> 经纬度
        geo_url = ("https://geocoding-api.open-meteo.com/v1/search?name="
                    + urllib.parse.quote(city_name) + "&count=1&language=zh")
        req = urllib.request.Request(geo_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=6) as r:
            geo = json.loads(r.read().decode("utf-8", "ignore"))
        results = geo.get("results") or []
        if not results:
            return f"没找到「{city_name}」对应的城市，无法查天气"
        lat, lon = results[0]["latitude"], results[0]["longitude"]
        real_name = results[0].get("name", city_name)

        # 2) 查当前天气
        wx_url = (f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
                  f"&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m&timezone=auto")
        req2 = urllib.request.Request(wx_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req2, timeout=6) as r:
            wx = json.loads(r.read().decode("utf-8", "ignore"))
        cur = wx.get("current", {})
        return (f"{real_name} 当前天气：{_weather_text(cur.get('weather_code'))}，"
                f"气温 {cur.get('temperature_2m')}℃，湿度 {cur.get('relative_humidity_2m')}%，"
                f"风速 {cur.get('wind_speed_10m')} km/h")
    except Exception as e:
        return f"天气查询失败：{type(e).__name__}，请稍后再试"


# ========== 定义工具列表，告诉大模型它能调用哪些函数 ==========
tools = [
    {
        "type": "function",
        "function": {
            "name": "generate_questions",
            "description": "生成指定方向的面试题",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {"type": "string", "description": "面试题方向，比如Python/FastAPI/MySQL/通信"}
                },
                "required": ["category"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_jobs",
            "description": "搜索岗位，可以按城市、优先级、是否国企筛选",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市，比如成都/绵阳/宜宾"},
                    "priority": {"type": "string", "description": "优先级，P0/P1/P2"},
                    "is_soe": {"type": "boolean", "description": "是否只要国企央企"}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询某个城市当前的天气和气温，城市比如成都/绵阳/宜宾/眉山",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，比如成都/绵阳/宜宾"}
                },
                "required": ["city"]
            }
        }
    }
]


# ========== Agent聊天接口（核心！） ==========
@app.post("/api/agent")
def agent_chat(message: str):
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[{"role": "user", "content": message}],
        tools=tools
    )

    if response.choices[0].message.tool_calls:
        tool_call = response.choices[0].message.tool_calls[0]

        if tool_call.function.name == "generate_questions":
            args = json.loads(tool_call.function.arguments)
            result = generate_questions(args["category"])
        elif tool_call.function.name == "search_jobs":
            args = json.loads(tool_call.function.arguments)
            result = search_jobs(
                city=args.get("city", ""),
                priority=args.get("priority", ""),
                is_soe=args.get("is_soe", False)
            )
        elif tool_call.function.name == "get_weather":
            args = json.loads(tool_call.function.arguments)
            result = get_weather(args.get("city", ""))
        else:
            result = "我暂时不会这个"
    else:
        result = response.choices[0].message.content

    return {"reply": result}


# ========== 根路径，返回首页 ==========
@app.get("/")
def home():
    return FileResponse("index.html")
