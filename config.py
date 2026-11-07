# -*- coding: utf-8 -*-
# 统一读取本地配置（密钥、数据库账号、数据源目录等）。
# 真实配置写在同目录的 .env 里（已被 .gitignore 排除，不会上传 GitHub）；
# 仓库里只保留 .env.example 模板，照着复制一份改成自己的值即可。
# 这里只用标准库解析，不依赖 python-dotenv。

import os


def _load_env():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.exists(env_path):
        return
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            value = value.strip().strip('"').strip("'")
            # 已存在的系统环境变量优先，不被 .env 覆盖
            os.environ.setdefault(key.strip(), value)


_load_env()


def get(key: str, default: str = "") -> str:
    """取环境变量，缺省返回 default。"""
    return os.environ.get(key, default)
