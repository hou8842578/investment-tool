from datetime import date, datetime

from flask import jsonify, request


def register_record_routes(app, deps):
    get_conn = deps['get_conn']
    get_current_user_id = deps['get_current_user_id']
    login_required = deps['login_required']
    get_record_list_for_user = deps['get_record_list_for_user']
    get_records_for_user = deps['get_records_for_user']
    get_record_row = deps['get_record_row']
    validate_record = deps['validate_record']
    parse_partner_fields = deps['parse_partner_fields']
    build_dashboard_payload = deps['build_dashboard_payload']

    @app.route('/api/records', methods=['GET'])
    @login_required
    def get_records():
        filter_type = request.args.get('filter')
        search = request.args.get('search', '')
        sort_key = request.args.get('sortKey', 'date')
        sort_dir = request.args.get('sortDir', 'desc')
        page = request.args.get('page')
        page_size = request.args.get('pageSize')
        with get_conn() as conn:
            if any(v is not None for v in [filter_type, page, page_size]) or search or request.args.get('sortKey') or request.args.get('sortDir'):
                return jsonify(get_record_list_for_user(
                    conn,
                    get_current_user_id(),
                    filter_type=filter_type or 'all',
                    search=search,
                    sort_key=sort_key,
                    sort_dir=sort_dir,
                    page=page or 1,
                    page_size=page_size or 15,
                ))
            return jsonify(get_records_for_user(conn, get_current_user_id()))

    @app.route('/api/dashboard', methods=['GET'])
    @login_required
    def get_dashboard():
        with get_conn() as conn:
            records = get_records_for_user(conn, get_current_user_id())
        return jsonify(build_dashboard_payload(records))

    @app.route('/api/records', methods=['POST'])
    @login_required
    def add_record():
        body = request.json or {}
        errors = validate_record(body)
        if errors:
            return jsonify({"ok": False, "msg": '；'.join(errors)}), 400

        now = datetime.now().isoformat(timespec='seconds')
        partner_name, partner_amount = parse_partner_fields(body)
        with get_conn() as conn:
            cur = conn.execute(
                '''
                INSERT INTO records (
                    user_id, date, amount, rate, days, return_date, actual_date,
                    interest, returned, return_month, final_interest, service_fee,
                    remark, partner_name, partner_amount, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    get_current_user_id(),
                    body.get('date', ''),
                    int(body.get('amount', 0)),
                    int(body.get('rate', 0)),
                    int(body.get('days', 0)),
                    body.get('returnDate', ''),
                    body.get('actualDate'),
                    int(body.get('interest', 0)),
                    1 if body.get('returned') else 0,
                    body.get('returnMonth'),
                    body.get('finalInterest'),
                    int(body.get('serviceFee', body.get('toLaoTan', 0)) or 0),
                    body.get('remark', ''),
                    partner_name,
                    partner_amount,
                    now,
                    now,
                )
            )
            new_id = cur.lastrowid
        return jsonify({"ok": True, "id": new_id})

    @app.route('/api/records/<int:rid>', methods=['PUT'])
    @login_required
    def update_record(rid):
        body = request.json or {}
        errors = validate_record(body)
        if errors:
            return jsonify({"ok": False, "msg": '；'.join(errors)}), 400

        partner_name, partner_amount = parse_partner_fields(body)
        with get_conn() as conn:
            row = get_record_row(conn, get_current_user_id(), rid)
            if not row:
                return jsonify({"ok": False, "msg": "未找到记录"}), 404
            conn.execute(
                '''
                UPDATE records
                SET date = ?, amount = ?, rate = ?, days = ?, return_date = ?, actual_date = ?,
                    interest = ?, returned = ?, return_month = ?, final_interest = ?,
                    service_fee = ?, remark = ?, partner_name = ?, partner_amount = ?, updated_at = ?
                WHERE id = ? AND user_id = ?
                ''',
                (
                    body.get('date', row['date']),
                    int(body.get('amount', row['amount'])),
                    int(body.get('rate', row['rate'])),
                    int(body.get('days', row['days'])),
                    body.get('returnDate', row['return_date']),
                    body.get('actualDate', row['actual_date']),
                    int(body.get('interest', row['interest'])),
                    1 if body.get('returned', bool(row['returned'])) else 0,
                    body.get('returnMonth', row['return_month']),
                    body.get('finalInterest', row['final_interest']),
                    int(body.get('serviceFee', body.get('toLaoTan', row['service_fee'])) or 0),
                    body.get('remark', row['remark']),
                    partner_name,
                    partner_amount,
                    datetime.now().isoformat(timespec='seconds'),
                    rid,
                    get_current_user_id(),
                )
            )
        return jsonify({"ok": True})

    @app.route('/api/records/<int:rid>', methods=['DELETE'])
    @login_required
    def delete_record(rid):
        with get_conn() as conn:
            cur = conn.execute(
                'DELETE FROM records WHERE id = ? AND user_id = ?',
                (rid, get_current_user_id())
            )
            if cur.rowcount == 0:
                return jsonify({"ok": False, "msg": "未找到记录"}), 404
        return jsonify({"ok": True})

    @app.route('/api/records/<int:rid>/return', methods=['POST'])
    @login_required
    def confirm_return(rid):
        body = request.json or {}
        with get_conn() as conn:
            row = get_record_row(conn, get_current_user_id(), rid)
            if not row:
                return jsonify({"ok": False, "msg": "未找到记录"}), 404
            actual_date = body.get('actualDate', date.today().isoformat())
            conn.execute(
                '''
                UPDATE records
                SET returned = 1,
                    actual_date = ?,
                    final_interest = ?,
                    service_fee = ?,
                    return_month = ?,
                    updated_at = ?
                WHERE id = ? AND user_id = ?
                ''',
                (
                    actual_date,
                    int(body.get('finalInterest', row['interest'])),
                    int(body.get('serviceFee', body.get('toLaoTan', 0)) or 0),
                    body.get('returnMonth', actual_date[:7]),
                    datetime.now().isoformat(timespec='seconds'),
                    rid,
                    get_current_user_id(),
                )
            )
        return jsonify({"ok": True})
