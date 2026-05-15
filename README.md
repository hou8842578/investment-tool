# 投资管理工具

一个基于 Flask 的固定收益投资记录工具，支持多用户账号、投资记录管理、回款确认、统计分析和数据导出。

## 当前能力

- 多用户注册、登录、改密
- 投资记录新增、编辑、删除、回款确认
- 合作方结构化录入与合作分账统计
- Dashboard 聚合统计
- 明细列表服务端筛选、搜索、排序、分页
- JSON / Excel / CSV 导出
- 基础 API 回归测试

## 技术栈

- Python 3.10+
- Flask
- SQLite
- openpyxl

## 目录结构

```text
.
├── app.py                  # Flask 入口、配置、依赖装配
├── auth_routes.py          # 认证接口注册
├── record_routes.py        # 记录与 dashboard 接口注册
├── misc_routes.py          # 页面、导出、通用接口注册
├── auth_service.py         # 认证业务逻辑
├── dashboard_service.py    # 统计聚合逻辑
├── export_service.py       # 导出逻辑
├── storage.py              # 数据初始化、迁移、查询、校验
├── templates/index.html    # 单页前端
├── tests/test_api.py       # 核心 API 回归测试
├── data.json               # 历史导入源
├── config.example.json     # 配置示例
└── requirements.txt        # 依赖清单
```

## 快速开始

1. 创建虚拟环境

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. 安装依赖

```bash
pip install -r requirements.txt
```

3. 启动项目

```bash
python3 app.py
```

4. 打开浏览器

```text
http://localhost:5000
```

## 首次启动行为

- 如果本地没有 `config.json`，应用会自动生成一个新的 `secret_key`
- 如果本地没有用户数据，应用会自动创建 `admin` 账号
- 如果存在历史 `data.json`，应用会把历史记录迁移到 `admin` 账号
- 如果没有旧密码哈希，默认管理员密码为 `admin123`

## 配置说明

- `config.json`
  - 运行时真实配置文件
  - 默认不会提交到仓库
- `config.example.json`
  - 配置示例文件
  - 可用于手动初始化部署环境

当前配置字段：

- `secret_key`: Flask session 密钥
- `password_hash`: 可选，管理员初始密码哈希

支持的环境变量：

- `INVEST_SECRET_KEY`: 直接覆盖 session 密钥
- `INVEST_DB_FILE`: 指定 SQLite 数据库路径
- `INVEST_CONFIG_FILE`: 指定配置文件路径
- `INVEST_DATA_FILE`: 指定历史导入源路径
- `INVEST_HOST`: 启动监听地址，默认 `0.0.0.0`
- `INVEST_PORT`: 启动端口，默认 `5000`
- `INVEST_SESSION_DAYS`: 登录会话有效天数，默认 `7`

## 测试

执行基础回归测试：

```bash
python3 -m unittest discover -s tests -v
```

测试覆盖：

- 注册、登录、改密
- 记录新增、编辑、回款、删除
- dashboard 聚合
- JSON / Excel 导出

## 导出说明

- `GET /api/export` 导出 JSON
- `GET /api/export/excel` 优先导出 Excel
- 如果环境缺少 `openpyxl`，会自动降级导出 CSV

## 启动命令

使用 `Makefile`：

```bash
make run
make test
make wsgi
make init-prod ARGS="--admin-username admin --db-file production/app.db --config-file production/config.json"
```

指定端口启动：

```bash
make dev PORT=8000
```

直接使用环境变量：

```bash
INVEST_PORT=8000 python3 app.py
```

## 部署准备

已提供 WSGI 入口文件：

- [wsgi.py](file:///Users/didi/Desktop/投资/wsgi.py)

本地模拟生产启动：

```bash
gunicorn -w 2 -b 0.0.0.0:8000 wsgi:app
```

或使用：

```bash
make wsgi PORT=8000
```

## 初始化生产库

生产环境建议不要直接复用当前开发库，可以先执行初始化脚本生成一份干净生产库：

```bash
python3 init_production_db.py \
  --admin-username admin \
  --db-file production/app.db \
  --config-file production/config.json
```

如果不传 `--admin-password`，脚本会交互式要求输入管理员密码。

常用参数：

- `--db-file`: 目标生产数据库路径
- `--config-file`: 目标生产配置文件路径
- `--admin-username`: 初始管理员账号
- `--admin-password`: 初始管理员密码
- `--secret-key`: 指定 secret_key；不传则自动生成
- `--force`: 允许覆盖已存在的目标文件

初始化完成后，使用环境变量指向这份生产库和配置：

```bash
INVEST_DB_FILE=production/app.db \
INVEST_CONFIG_FILE=production/config.json \
gunicorn -w 2 -b 0.0.0.0:8000 wsgi:app
```

## 当前架构说明

- 路由层负责请求分发和依赖调用
- service 层负责认证、统计、导出等业务逻辑
- storage 层负责数据库初始化、历史迁移、记录查询和数据校验
- 前端仍为单页模板，但核心统计和列表查询已经迁到后端

## 已知说明

- 当前仍使用 Flask 开发服务器，适合本地和内网试用，不适合直接生产部署
- 数据库存储使用 SQLite，适合当前体量；后续如果正式开放，可迁移到 MySQL 或 PostgreSQL
