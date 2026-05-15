# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

多用户固定收益投资记录工具，用于跟踪投出、回款、利息、服务费和合作分账。历史数据来源于 Excel，当前运行时存储已迁移到 SQLite。

## 启动方式

```bash
pip install -r requirements.txt
python3 app.py
# 访问 http://localhost:5000
```

也支持：

```bash
make run
make test
make wsgi PORT=8000
```

## 架构

当前后端已经拆为“入口 + 路由 + service + storage”结构：

- `app.py` — Flask 入口、配置加载、数据库连接、依赖装配、路由注册
- `auth_routes.py` — 注册、登录、登出、改密、登录状态接口
- `record_routes.py` — 记录 CRUD、回款确认、dashboard、列表查询接口
- `misc_routes.py` — 页面、导出、今日日期接口
- `auth_service.py` — 认证业务逻辑
- `dashboard_service.py` — 统计聚合逻辑
- `export_service.py` — 导出逻辑
- `storage.py` — 数据初始化、历史迁移、查询、分页、记录校验
- `templates/index.html` — 单页前端，内联 CSS + JS
- `app.db` — 运行时 SQLite 数据库
- `data.json` — 历史导入源
- `在老谭投资表.xlsx` — 原始 Excel 数据源
- `投资记录.html` — 历史静态版本
- `wsgi.py` — 生产部署入口
- `Makefile` — 常用运行/测试命令

## API 路由

| 方法 | 路径 | 用途 |
|------|------|------|
| POST | `/api/register` | 注册并自动登录 |
| POST | `/api/login` | 登录 |
| POST | `/api/logout` | 登出 |
| GET | `/api/check-auth` | 获取登录状态 |
| POST | `/api/change-password` | 修改密码 |
| GET | `/api/records` | 获取记录或分页查询 |
| POST | `/api/records` | 新增记录 |
| PUT | `/api/records/<id>` | 更新记录 |
| DELETE | `/api/records/<id>` | 删除记录 |
| POST | `/api/records/<id>/return` | 确认回款 |
| GET | `/api/dashboard` | 获取 dashboard 聚合统计 |
| GET | `/api/export` | 导出 JSON 文件 |
| GET | `/api/export/excel` | 导出 Excel/CSV 文件 |
| GET | `/api/today` | 获取今日日期 |

## 关键业务逻辑

- **利息计算**：`amount / 10000 * rate`（金额除以一万乘以每万利息）
- **计划回款日期**：投资日期 + 天数
- `returned=false` 的记录为待回款状态，后端会聚合逾期和近期待回款提醒
- `serviceFee` 字段记录服务费，兼容旧字段 `toLaoTan`
- 合作分账已结构化为 `partnerName` / `partnerAmount`
- 历史备注中的“青山”“有青山10万”等写法仍会在迁移时兼容解析

## 测试

项目已包含基础 API 回归测试：

```bash
python3 -m unittest discover -s tests -v
```

覆盖范围：

- 注册、登录、改密
- 记录新增、编辑、回款、删除
- dashboard 聚合
- JSON / Excel 导出

## 环境变量

- `INVEST_SECRET_KEY`
- `INVEST_DB_FILE`
- `INVEST_CONFIG_FILE`
- `INVEST_DATA_FILE`
- `INVEST_HOST`
- `INVEST_PORT`
- `INVEST_SESSION_DAYS`
