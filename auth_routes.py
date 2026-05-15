from flask import jsonify, request, session


def register_auth_routes(app, deps):
    get_conn = deps['get_conn']
    get_current_user_id = deps['get_current_user_id']
    get_user_by_username = deps['get_user_by_username']
    login_required = deps['login_required']
    register_user = deps['register_user']
    authenticate_user = deps['authenticate_user']
    set_login_session = deps['set_login_session']
    clear_login_session = deps['clear_login_session']
    build_auth_status = deps['build_auth_status']
    update_password = deps['update_password']

    @app.route('/api/register', methods=['POST'])
    def register():
        body = request.json or {}
        with get_conn() as conn:
            user, err, status = register_user(
                conn,
                body.get('username', ''),
                body.get('password', ''),
                get_user_by_username,
            )
        if err:
            return jsonify({'ok': False, 'msg': err}), status
        set_login_session(session, user)
        return jsonify({'ok': True, 'username': user['username'], 'is_admin': bool(user['is_admin'])})

    @app.route('/api/login', methods=['POST'])
    def login():
        body = request.json or {}
        with get_conn() as conn:
            user = authenticate_user(
                conn,
                body.get('username', ''),
                body.get('password', ''),
                get_user_by_username,
            )
        if not user:
            return jsonify({"ok": False, "msg": "账号或密码错误"}), 403
        set_login_session(session, user)
        return jsonify({"ok": True, "username": user['username'], "is_admin": bool(user['is_admin'])})

    @app.route('/api/logout', methods=['POST'])
    def logout():
        clear_login_session(session)
        return jsonify({"ok": True})

    @app.route('/api/check-auth', methods=['GET'])
    def check_auth():
        return jsonify(build_auth_status(session))

    @app.route('/api/change-password', methods=['POST'])
    @login_required
    def change_password():
        body = request.json or {}
        with get_conn() as conn:
            err, status = update_password(
                conn,
                get_current_user_id(),
                body.get('old_password', ''),
                body.get('new_password', ''),
            )
        if err:
            return jsonify({'ok': False, 'msg': err}), status
        return jsonify({"ok": True})
