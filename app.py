"""
投资管理工具 - Flask 应用
启动: python3 app.py
访问: http://localhost:5000
默认账号: admin
默认密码: admin123（首次迁移后请及时修改）
"""

from flask import Flask, jsonify, session
import json
import os
import sqlite3
import uuid
from datetime import timedelta
from functools import wraps
from auth_service import (
    authenticate_user,
    build_auth_status,
    clear_login_session,
    hash_password,
    register_user,
    set_login_session,
    update_password,
    validate_password,
)
from admin_service import build_admin_overview, list_users_with_stats, reset_user_password
from dashboard_service import build_dashboard_payload
from export_service import export_excel_or_csv_response, export_json_response
from admin_routes import register_admin_routes
from auth_routes import register_auth_routes
from misc_routes import register_misc_routes
from record_routes import register_record_routes
from storage import (
    get_record_list_for_user,
    get_record_row,
    get_records_for_user,
    get_user_by_username,
    init_db,
    parse_partner_fields,
    validate_record,
)

try:
    from openpyxl import Workbook
    HAS_EXCEL = True
except ImportError:
    HAS_EXCEL = False

app = Flask(__name__)

# ===================== 配置 =====================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def get_path_from_env(env_name, default_name):
    return os.getenv(env_name, os.path.join(BASE_DIR, default_name))


DATA_FILE = get_path_from_env('INVEST_DATA_FILE', 'data.json')
CONFIG_FILE = get_path_from_env('INVEST_CONFIG_FILE', 'config.json')
DB_FILE = get_path_from_env('INVEST_DB_FILE', 'app.db')
SESSION_DAYS = int(os.getenv('INVEST_SESSION_DAYS', '7'))
app.permanent_session_lifetime = timedelta(days=SESSION_DAYS)


def load_config():
    """加载配置，首次运行自动创建"""
    env_secret = os.getenv('INVEST_SECRET_KEY')
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)
    else:
        config = {}
    if env_secret:
        config['secret_key'] = env_secret
    if not config.get('secret_key'):
        config['secret_key'] = uuid.uuid4().hex
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    return config


config = load_config()
app.secret_key = config['secret_key']


# ===================== 认证 =====================

def login_required(f):
    """需要登录才能访问的接口"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({"ok": False, "msg": "请先登录"}), 401
        return f(*args, **kwargs)
    return decorated


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('user_id'):
            return jsonify({"ok": False, "msg": "请先登录"}), 401
        if not session.get('is_admin'):
            return jsonify({"ok": False, "msg": "需要管理员权限"}), 403
        return f(*args, **kwargs)
    return decorated


def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn


def get_current_user_id():
    return session.get('user_id')


def get_current_username():
    return session.get('username')


def get_current_is_admin():
    return bool(session.get('is_admin'))


# ===================== 数据层 =====================
DB_WAS_SEEDED = init_db(get_conn, config, DATA_FILE, hash_password)

register_auth_routes(app, {
    'get_conn': get_conn,
    'get_current_user_id': get_current_user_id,
    'get_user_by_username': get_user_by_username,
    'login_required': login_required,
    'register_user': register_user,
    'authenticate_user': authenticate_user,
    'set_login_session': set_login_session,
    'clear_login_session': clear_login_session,
    'build_auth_status': build_auth_status,
    'update_password': update_password,
})

register_record_routes(app, {
    'get_conn': get_conn,
    'get_current_user_id': get_current_user_id,
    'login_required': login_required,
    'get_record_list_for_user': get_record_list_for_user,
    'get_records_for_user': get_records_for_user,
    'get_record_row': get_record_row,
    'validate_record': validate_record,
    'parse_partner_fields': parse_partner_fields,
    'build_dashboard_payload': build_dashboard_payload,
})

register_admin_routes(app, {
    'get_conn': get_conn,
    'admin_required': admin_required,
    'build_admin_overview': build_admin_overview,
    'list_users_with_stats': list_users_with_stats,
    'reset_user_password': reset_user_password,
    'validate_password': validate_password,
})

register_misc_routes(app, {
    'get_conn': get_conn,
    'get_current_user_id': get_current_user_id,
    'get_current_username': get_current_username,
    'get_current_is_admin': get_current_is_admin,
    'get_records_for_user': get_records_for_user,
    'login_required': login_required,
    'export_json_response': export_json_response,
    'export_excel_or_csv_response': export_excel_or_csv_response,
    'has_excel': HAS_EXCEL,
    'workbook_cls': Workbook if HAS_EXCEL else None,
})


# ===================== 启动 =====================

if __name__ == '__main__':
    host = os.getenv('INVEST_HOST', '0.0.0.0')
    port = int(os.getenv('INVEST_PORT', '5000'))
    print("=" * 40)
    print("  投资管理工具已启动")
    print(f"  访问: http://localhost:{port}")
    if DB_WAS_SEEDED:
        print("  已完成首轮迁移：历史数据已导入 admin 账号")
        print("  默认账号: admin")
        print("  默认密码沿用旧系统密码；若无旧密码则为 admin123")
    print("=" * 40)
    app.run(host=host, port=port)
