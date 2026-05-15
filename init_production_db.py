import argparse
import json
import os
import secrets
import sqlite3
import sys
from datetime import datetime
from getpass import getpass
from pathlib import Path

from auth_service import hash_password, validate_password, validate_username
from storage import ensure_schema, get_user_by_username


def build_parser():
    parser = argparse.ArgumentParser(description='初始化生产环境数据库与管理员账号')
    parser.add_argument('--db-file', default='production/app.db', help='生产 SQLite 数据库路径')
    parser.add_argument('--config-file', default='production/config.json', help='生产配置文件路径')
    parser.add_argument('--admin-username', default='admin', help='管理员账号，默认 admin')
    parser.add_argument('--admin-password', default='', help='管理员密码；未传时将交互输入')
    parser.add_argument('--secret-key', default='', help='Flask secret_key；未传时自动生成')
    parser.add_argument('--force', action='store_true', help='如果目标文件已存在则覆盖')
    return parser


def ensure_parent_dir(file_path):
    Path(file_path).parent.mkdir(parents=True, exist_ok=True)


def validate_inputs(username, password):
    username_err = validate_username(username)
    if username_err:
        raise ValueError(username_err)
    password_err = validate_password(password)
    if password_err:
        raise ValueError(password_err)


def initialize_production_database(db_file, config_file, admin_username, admin_password, secret_key, force=False):
    validate_inputs(admin_username, admin_password)

    db_path = Path(db_file)
    config_path = Path(config_file)

    if db_path.exists() and not force:
        raise FileExistsError(f'数据库文件已存在：{db_path}')
    if config_path.exists() and not force:
        raise FileExistsError(f'配置文件已存在：{config_path}')

    ensure_parent_dir(db_path)
    ensure_parent_dir(config_path)

    if db_path.exists():
        db_path.unlink()
    if config_path.exists():
        config_path.unlink()

    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        ensure_schema(conn)
        created_at = datetime.now().isoformat(timespec='seconds')
        conn.execute(
            'INSERT INTO users (username, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?)',
            (admin_username.strip(), hash_password(admin_password), 1, created_at),
        )
        conn.commit()

        if not get_user_by_username(conn, admin_username):
            raise RuntimeError('管理员账号创建失败')

        config = {
            'secret_key': secret_key or secrets.token_hex(32),
            'initialized_for': 'production',
            'created_at': created_at,
        }
        config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
    finally:
        conn.close()

    return {
        'db_file': str(db_path),
        'config_file': str(config_path),
        'admin_username': admin_username.strip(),
    }


def main():
    parser = build_parser()
    args = parser.parse_args()
    admin_password = args.admin_password or getpass('请输入管理员密码（至少4位）：')

    try:
        result = initialize_production_database(
            db_file=args.db_file,
            config_file=args.config_file,
            admin_username=args.admin_username,
            admin_password=admin_password,
            secret_key=args.secret_key,
            force=args.force,
        )
    except Exception as exc:
        print(f'初始化失败：{exc}', file=sys.stderr)
        sys.exit(1)

    print('生产库初始化完成')
    print(f"数据库: {result['db_file']}")
    print(f"配置: {result['config_file']}")
    print(f"管理员账号: {result['admin_username']}")
    print('请使用环境变量指向这两份生产文件后再启动应用')


if __name__ == '__main__':
    main()
