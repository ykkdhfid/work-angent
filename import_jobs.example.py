# -*- coding: utf-8 -*-
# 岗位初始化导入模板。
# 复制为 import_jobs.py，把岗位填进 jobs_data 后运行：python import_jobs.py
# import_jobs.py 属于私人岗位清单，已被 .gitignore 排除，不上传 GitHub。

from database import SessionLocal, Job

jobs_data = [
    # 示例（按需增删）：
    # {"company": "公司名", "position": "岗位名", "city": "成都", "salary": "面议",
    #  "priority": "P0", "job_type": "实习", "is_soe": False, "url": "https://...",
    #  "description": "岗位说明"},
]

db = SessionLocal()
for job_data in jobs_data:
    db.add(Job(**job_data))
db.commit()
print(f"成功导入 {len(jobs_data)} 个岗位！")
db.close()
