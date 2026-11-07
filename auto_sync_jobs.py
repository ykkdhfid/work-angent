# -*- coding: utf-8 -*-
# 岗位巡检同步脚本
# 解析求职中心 HTML 的岗位清单，同步到 MySQL jobs 表：
#   1) 在招岗位：新增或更新
#   2) 已停止招聘岗位：自动从数据库删除，并记录删除原因
#   3) 库里有、本次清单已没有的岗位：视为下架，自动删除
# 数据源不可用或解析不到岗位时跳过本次，不清空数据库（防止误删）

import glob
import os
import re
from datetime import date, datetime

from database import SessionLocal, Job
from config import get

# 求职中心 HTML 所在目录（由每日同步脚本下载到本地），按文件名前缀匹配最新一份
# 目录从环境变量或 .env 读取，不在代码里写死本地路径
CENTER_DIR = get("JOB_CENTER_DIR", "")
# 同步日志文件（放在本脚本同目录，按行追加）
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "_sync_jobs_log.txt")


def _find_center_html():
    """在求职中心目录里找“求职中心”开头的 HTML，返回最新修改的一份；找不到返回空串。"""
    candidates = glob.glob(os.path.join(CENTER_DIR, "求职中心*.html"))
    if not candidates:
        return ""
    return max(candidates, key=os.path.getmtime)

# 判定停止招聘的文案关键词
STOP_KEYWORDS = ["已下线", "已截止", "招满", "停止招聘", "已关闭", "勿再投递", "已结束", "已停招"]


def _field(block, name):
    """从单个岗位对象块里取字符串字段。"""
    m = re.search(name + r'\s*:\s*"([^"]*)"', block)
    return m.group(1).strip() if m else ""


def _parse_deadline(block):
    """从块里解析截止日期，解析失败返回 None。"""
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", block)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(0), "%Y-%m-%d").date()
    except ValueError:
        return None


def is_stopped(block, role, reason, deadline):
    """返回停止招聘原因；在招返回空字符串。"""
    # 1) 数据源里显式标了 closed:true
    if re.search(r"closed\s*:\s*true", block):
        return "标记已下线"
    # 2) 岗位名或说明文案命中停止关键词
    text = role + " " + reason
    for kw in STOP_KEYWORDS:
        if kw in text:
            return "文案标注：" + kw
    # 3) 截止日期早于今天
    if deadline and deadline < date.today():
        return "截止日期已过：" + deadline.isoformat()
    return ""


def _is_soe(company):
    return any(k in company for k in ["国企", "央企", "移动", "电信", "联通", "长虹", "九洲"])


def _priority(p):
    p = (p or "").lower()
    if p in ("p0", "p1", "p2"):
        return p.upper()
    if p == "campus":
        return "校招"
    return "P2"


def _job_type(p):
    return "秋招正式" if (p or "").lower() == "campus" else "实习"


# ===== 岗位方向过滤 =====
# 白名单：岗位名或说明命中任一关键词才保留（小写匹配）；留空表示不做白名单限制
INCLUDE_KEYWORDS = ["python", "测试", "大模型", "算法", "后端", "rpa", "数据", "agent", "ai"]
# 黑名单：命中任一关键词直接剔除（小写匹配），比如明确不投的方向
EXCLUDE_KEYWORDS = ["java", "安卓", "android"]


def _match_direction(job):
    """按白/黑名单判断岗位是否属于目标方向；不符合返回 False。"""
    text = (job["position"] + " " + job["description"]).lower()
    if any(k in text for k in EXCLUDE_KEYWORDS):
        return False
    if not INCLUDE_KEYWORDS:
        return True
    return any(k in text for k in INCLUDE_KEYWORDS)


def parse_jobs(html_text):
    """把 HTML 里的 jobs 数组解析成岗位字典列表。"""
    start = html_text.find("const jobs = [")
    if start == -1:
        return []
    end = html_text.find("];", start)
    section = html_text[start:end if end != -1 else len(html_text)]

    jobs = []
    for block in re.findall(r"\{[^{}]*\}", section):
        company = _field(block, "co")
        role = _field(block, "role")
        if not company or not role:
            continue
        reason = _field(block, "reason")
        deadline = _parse_deadline(block)
        jobs.append({
            "company": company,
            "position": role,
            "city": _field(block, "city"),
            "salary": _field(block, "sal"),
            "url": _field(block, "url"),
            "priority": _priority(_field(block, "p")),
            "job_type": _job_type(_field(block, "p")),
            "is_soe": _is_soe(company),
            "description": reason,
            "deadline": deadline,
            "stop_reason": is_stopped(block, role, reason, deadline),
        })
    return jobs


def append_log(message):
    stamp = date.today().isoformat() + " " + datetime.now().strftime("%H:%M:%S")
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(stamp + " " + message + "\n")


def sync_jobs():
    # 数据源保护：文件缺失 / 过期占位 / 内容过小，都跳过且不动库
    html_path = _find_center_html()
    if not html_path:
        append_log("SKIP 未找到求职中心 HTML，本次未改动数据库")
        print("未找到数据源文件，跳过")
        return
    try:
        with open(html_path, "r", encoding="utf-8") as f:
            html_text = f.read()
    except FileNotFoundError:
        append_log("SKIP 数据源文件不存在，本次未改动数据库")
        print("数据源文件不存在，跳过")
        return

    if len(html_text) < 100 or "url is expired" in html_text:
        append_log("SKIP 数据源已过期或为空，本次未改动数据库")
        print("数据源不可用，跳过，不清库")
        return

    jobs = parse_jobs(html_text)
    # 按目标方向过滤：不符方向的岗位不入库
    before = len(jobs)
    jobs = [j for j in jobs if _match_direction(j)]
    filtered = before - len(jobs)
    if filtered:
        append_log("FILTER 方向不符剔除 %d 个岗位" % filtered)
    if not jobs:
        append_log("SKIP 未解析到有效岗位，本次未改动数据库")
        print("未解析到岗位，跳过，不清库")
        return

    db = SessionLocal()
    try:
        existing = {(j.company.strip(), j.position.strip()): j for j in db.query(Job).all()}
        active_keys = set()
        added = updated = removed = offline = 0

        for job in jobs:
            key = (job["company"].strip(), job["position"].strip())

            # 已停止招聘：库中存在则删除
            if job["stop_reason"]:
                if key in existing:
                    db.delete(existing[key])
                    removed += 1
                    append_log("DELETE 已停止招聘：%s | %s（%s）" % (
                        job["company"], job["position"], job["stop_reason"]))
                continue

            # 在招岗位：新增或更新
            active_keys.add(key)
            row = existing.get(key)
            if row:
                row.city = job["city"]
                row.salary = job["salary"]
                row.priority = job["priority"]
                row.job_type = job["job_type"]
                row.is_soe = job["is_soe"]
                row.url = job["url"]
                row.description = job["description"]
                updated += 1
            else:
                row_data = {k: v for k, v in job.items() if k not in ("deadline", "stop_reason")}
                db.add(Job(**row_data))
                added += 1

        # 库中存在、本次清单已没有：视为下架，删除
        for key, row in existing.items():
            if key not in active_keys:
                db.delete(row)
                offline += 1
                append_log("DELETE 清单已下架：%s | %s" % (row.company, row.position))

        db.commit()
        summary = "SYNC 完成：新增 %d，更新 %d，停止招聘删除 %d，下架删除 %d，在招留存 %d" % (
            added, updated, removed, offline, len(active_keys))
        append_log(summary)
        print(summary)
    finally:
        db.close()


if __name__ == "__main__":
    sync_jobs()
