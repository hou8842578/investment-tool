from flask import jsonify, request


def register_admin_routes(app, deps):
    get_conn = deps['get_conn']
    admin_required = deps['admin_required']
    build_admin_overview = deps['build_admin_overview']
    list_users_with_stats = deps['list_users_with_stats']
    reset_user_password = deps['reset_user_password']
    validate_password = deps['validate_password']

    @app.route('/api/admin/overview', methods=['GET'])
    @admin_required
    def admin_overview():
        with get_conn() as conn:
            return jsonify(build_admin_overview(conn))

    @app.route('/api/admin/users', methods=['GET'])
    @admin_required
    def admin_users():
        with get_conn() as conn:
            return jsonify({'items': list_users_with_stats(conn)})

    @app.route('/api/admin/users/<int:user_id>/reset-password', methods=['POST'])
    @admin_required
    def admin_reset_password(user_id):
        body = request.json or {}
        with get_conn() as conn:
            err, status = reset_user_password(
                conn,
                user_id,
                body.get('newPassword', ''),
                validate_password,
            )
        if err:
            return jsonify({'ok': False, 'msg': err}), status
        return jsonify({'ok': True})
