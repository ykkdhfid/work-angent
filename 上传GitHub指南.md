# 上传 GitHub 操作指南

这份文档说明怎么把本项目上传（推送）到 GitHub。按步骤照抄命令即可，命令在 Windows 的 PowerShell 里也能用。

## 0. 前置准备

1. 安装 Git for Windows（官网下载安装，一路默认即可）。
2. 注册并登录 GitHub，本项目远程仓库地址：

```
https://github.com/ykkdhfid/work-angent.git
```

3. 如果命令行提示 `git 不是内部或外部命令`：把 Git 安装目录下的 `cmd` 文件夹加进系统环境变量 `Path`，重启终端；或直接用 Git 安装目录里的完整路径调用 `git.exe`。

## 1. 一次性配置身份

只需做一次，换成你自己的 GitHub 用户名和邮箱：

```bash
git config --global user.name "你的GitHub用户名"
git config --global user.email "你的GitHub邮箱"
```

## 2. 首次上传整个项目

在项目文件夹里打开终端，依次执行：

```bash
# 1) 把当前文件夹变成 git 仓库（已经是仓库就跳过这步）
git init -b master

# 2) 把要上传的文件加入暂存区（.gitignore 里列的文件不会被加入）
git add .

# 3) 提交到本地仓库，括号里写本次改动说明
git commit -m "初始化项目"

# 4) 关联远程仓库
git remote add origin https://github.com/ykkdhfid/work-angent.git

# 5) 推送到远程并关联分支
git push -u origin master
```

> 如果 GitHub 新建仓库默认分支叫 `main`，把上面命令里的 `master` 换成 `main`；也可以在 GitHub 仓库设置里把默认分支改成 `master`。

## 3. 以后改完代码再推送

日常更新只需要三步：

```bash
# 1) 加入改动
git add .

# 2) 提交，写清这次改了什么
git commit -m "说明本次改动"

# 3) 推送
git push origin master
```

## 4. 哪些文件不会上传

`.gitignore` 已经把下面这些排除在仓库外，不会推到 GitHub：

- `.env`：本地密钥、数据库密码、巡检目录等私密配置
- `import_jobs.py`：私人岗位清单
- `__pycache__/`、`*.pyc`：Python 缓存
- `.idea/`、`.vscode/`：IDE 配置
- 废弃草稿、备份 HTML、日志和临时文件

> 提醒：密钥和密码只放在本地 `.env` 里，不要写进代码，也不要提交到仓库。

## 5. 常见报错处理

### 推送时要求登录 / 认证失败

- HTTPS 方式推送需要 GitHub 凭据。弹出登录窗口时用 GitHub 账号登录；若用令牌（Token）认证，密码处填 Personal Access Token，不是 GitHub 登录密码。
- 也可以改用 SSH 方式：在 GitHub 配置好 SSH 公钥后，远程地址换成 `git@github.com:ykkdhfid/work-angent.git`。

### `! [rejected] master -> master (fetch first)`

远程已有别人或别处推上去的提交，先拉取合并再推：

```bash
git pull origin master --rebase
git push origin master
```

### 远程历史需要强制覆盖（谨慎使用）

只有确认本地仓库就是想要的完整版本、要丢掉远程旧历史时，才用强制推送：

```bash
git push origin master --force
```

### 想看当前状态和已改动文件

```bash
git status
git log --oneline
```

## 6. 本项目当前状态

本项目已经是 git 仓库并关联好了上述远程地址，日常改完直接走第 3 节的 `add → commit → push` 三步即可，不需要再 `git init` 或 `remote add`。
