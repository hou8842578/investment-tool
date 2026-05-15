import hashlib
import re
from datetime import datetime


def hash_password(password):
    return hashlib.sha256((password or '').encode()).hexdigest()


def validate_username(username):
    username = (username or '').strip()
    if len(username) < 3 or len(username) > 20:
        return '账号长度需为3到20位'
    if re.search(r'\s', username):
        return '账号不能包含空格'
    return None


def validate_password(password):
    if len(password or '') < 4:
        return '密码至少4位'
    return None


def register_user(conn, username, password, get_user_by_username):
    username = (username or '').strip()
    err = validate_username(username)
    if err:
        return None, err, 400
    err = validate_password(password)
    if err:
        return None, err, 400
    if get_user_by_username(conn, username):
        return None, '账号已存在', 409

    conn.execute(
        'INSERT INTO users (username, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?)',
        (username, hash_password(password), 0, datetime.now().isoformat(timespec='seconds'))
    )
    return get_user_by_username(conn, username), None, 200


def authenticate_user(conn, username, password, get_user_by_username):
    username = (username or '').strip()
    user = get_user_by_username(conn, username)
    if not user or hash_password(password) != user['password_hash']:
        return None
    return user


def update_password(conn, user_id, old_password, new_password):
    err = validate_password(new_password)
    if err:
        return err, 400

    user = conn.execute(
        'SELECT id, password_hash FROM users WHERE id = ?',
        (user_id,)
    ).fetchone()
    if not user or hash_password(old_password) != user['password_hash']:
        return '原密码错误', 403

    conn.execute(
        'UPDATE users SET password_hash = ? WHERE id = ?',
        (hash_password(new_password), user['id'])
    )
    return None, 200


def set_login_session(session_obj, user):
    session_obj['user_id'] = user['id']
    session_obj['username'] = user['username']
    session_obj['is_admin'] = bool(user['is_admin'])
    session_obj.permanent = True


def clear_login_session(session_obj):
    session_obj.pop('user_id', None)
    session_obj.pop('username', None)
    session_obj.pop('is_admin', None)


def build_auth_status(session_obj):
    return {
        'logged_in': bool(session_obj.get('user_id')),
        'username': session_obj.get('username'),
        'is_admin': bool(session_obj.get('is_admin')),
    }
