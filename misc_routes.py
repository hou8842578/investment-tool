from datetime import date

from flask import jsonify, render_template


def register_misc_routes(app, deps):
    get_conn = deps['get_conn']
    get_current_user_id = deps['get_current_user_id']
    get_current_username = deps['get_current_username']
    get_records_for_user = deps['get_records_for_user']
    login_required = deps['login_required']
    export_json_response = deps['export_json_response']
    export_excel_or_csv_response = deps['export_excel_or_csv_response']
    has_excel = deps['has_excel']
    workbook_cls = deps['workbook_cls']

    @app.route('/')
    def index():
        today = date.today().isoformat()
        return render_template('index.html', today=today)

    @app.route('/api/export', methods=['GET'])
    @login_required
    def export_data():
        with get_conn() as conn:
            data = get_records_for_user(conn, get_current_user_id())
        return export_json_response(data, get_current_username())

    @app.route('/api/export/excel', methods=['GET'])
    @login_required
    def export_excel():
        with get_conn() as conn:
            data = get_records_for_user(conn, get_current_user_id())
        return export_excel_or_csv_response(
            data,
            get_current_username(),
            has_excel,
            workbook_cls if has_excel else None,
        )

    @app.route('/api/today', methods=['GET'])
    def get_today():
        return jsonify({"today": date.today().isoformat()})
