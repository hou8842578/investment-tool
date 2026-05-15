import json
import os
import re
from datetime import datetime


def validate_record(body):
    errors = []
    try:
        amount = int(body.get('amount', 0))
        if amount <= 0 or amount > 10000000:
            errors.append('投资金额应在1~1000万之间')
    except (ValueError, TypeError):
        errors.append('投资金额格式不正确')
    try:
        rate = int(body.get('rate', 0))
        if rate <= 0 or rate > 10000:
            errors.append('利息/万应在1~10000之间')
    except (ValueError, TypeError):
        errors.append('利息/万格式不正确')
    try:
        days = int(body.get('days', 0))
        if days < 0 or days > 365:
            errors.append('投资天数应在0~365之间')
    except (ValueError, TypeError):
        errors.append('投资天数格式不正确')
    date_str = body.get('date', '')
    if not date_str or not re.match(r'^\d{4}-\d{2}-\d{2}$', date_str):
        errors.append('投资日期格式不正确')
    try:
        partner_amount = int(body.get('partnerAmount', 0) or 0)
        if partner_amount < 0:
            errors.append('合作出资不能小于0')
        elif amount > 0 and partner_amount > amount:
            errors.append('合作出资不能大于投资金额')
    except (ValueError, TypeError, UnboundLocalError):
        errors.append('合作出资格式不正确')
    return errors


def parse_partner_fields(record):
    partner_name = (record.get('partnerName') or '').strip()
    raw_partner_amount = record.get('partnerAmount', 0)
    try:
        partner_amount = int(raw_partner_amount or 0)
    except (ValueError, TypeError):
        partner_amount = 0
    if partner_name or partner_amount:
        return partner_name, max(partner_amount, 0)

    remark = (record.get('remark') or '').strip()
    amount = int(record.get('amount', 0) or 0)
    match = re.search(r'有青山(\d+)万', remark)
    if match:
        return '青山', int(match.group(1)) * 10000
    match = re.search(r'有青山(\d+)', remark)
    if match:
        return '青山', int(match.group(1))
    if remark == '青山':
        return '青山', amount
    return '', 0


def get_initial_data():
    rows = [
        ("2025-01-17",50000,640,0,"2025-02-19","2025-02-19",3200,True,"2025-02",3200,200,""),
        ("2025-01-28",100000,300,0,"2025-02-24","2025-02-24",3000,True,"2025-02",3000,0,""),
        ("2025-02-14",100000,350,27,"2025-03-13","2025-03-14",3500,True,"2025-03",3500,0,""),
        ("2025-02-21",140000,330,28,"2025-03-21","2025-03-24",4620,True,"2025-03",4620,200,""),
        ("2025-02-20",100000,540,38,"2025-03-30","2025-04-01",5400,True,"2025-04",5200,0,""),
        ("2025-03-03",100000,330,27,"2025-03-30","2025-04-04",3300,True,"2025-04",3300,0,""),
        ("2025-03-17",100000,520,38,"2025-04-24","2025-05-07",5200,True,"2025-05",5200,200,""),
        ("2025-03-24",100000,280,27,"2025-04-20","2025-04-22",2800,True,"2025-04",2800,200,""),
        ("2025-03-27",200000,320,28,"2025-04-24","2025-04-29",6400,True,"2025-04",6400,0,""),
        ("2025-04-03",200000,300,28,"2025-05-01","2025-05-06",6000,True,"2025-05",6000,0,""),
        ("2025-04-21",120000,320,28,"2025-05-19","2025-05-22",3840,True,"2025-05",3840,0,""),
        ("2025-04-28",200000,310,30,"2025-05-28","2025-05-30",6200,True,"2025-05",6200,0,""),
        ("2025-05-03",100000,520,46,"2025-06-18","2025-06-20",5200,True,"2025-06",5200,0,""),
        ("2025-05-01",200000,310,30,"2025-05-31","2025-06-06",6200,True,"2025-06",6200,0,""),
        ("2025-05-07",100000,310,30,"2025-06-06","2025-06-10",3100,True,"2025-06",3100,0,""),
        ("2025-05-08",170000,300,30,"2025-06-07","2025-06-13",5100,True,"2025-06",5100,200,""),
        ("2025-05-26",200000,310,28,"2025-06-23","2025-06-27",6200,True,"2025-06",6200,0,""),
        ("2025-05-26",90000,480,39,"2025-07-04","2025-07-09",4320,True,"2025-07",4320,0,""),
        ("2025-05-30",180000,300,30,"2025-06-29","2025-07-02",5400,True,"2025-07",5400,200,""),
        ("2025-06-08",200000,290,30,"2025-07-08","2025-07-17",5800,True,"2025-07",5800,0,""),
        ("2025-06-08",100000,300,30,"2025-07-08","2025-07-18",3000,True,"2025-07",0,0,"青山"),
        ("2025-06-15",200000,300,30,"2025-07-15","2025-07-28",6000,True,"2025-07",6000,0,""),
        ("2025-06-22",100000,480,49,"2025-08-10","2025-08-26",4800,True,"2025-08",4800,0,""),
        ("2025-06-23",200000,290,30,"2025-07-23","2025-08-01",5800,True,"2025-08",5800,0,""),
        ("2025-07-04",200000,280,35,"2025-08-08","2025-08-19",5600,True,"2025-08",5600,200,""),
        ("2025-07-04",100000,290,35,"2025-08-08","2025-08-12",2900,True,"2025-08",2900,0,""),
        ("2025-07-18",130000,290,35,"2025-08-22","2025-09-08",3770,True,"2025-09",3770,0,""),
        ("2025-07-19",200000,290,35,"2025-08-23","2025-09-05",5800,True,"2025-09",5800,0,""),
        ("2025-07-31",200000,290,35,"2025-09-04","2025-09-19",5800,True,"2025-09",5800,200,""),
        ("2025-07-31",200000,280,35,"2025-09-04","2025-09-18",5600,True,"2025-09",5600,0,""),
        ("2025-08-06",180000,280,35,"2025-09-10","2025-09-28",5040,True,"2025-09",0,0,"青山"),
        ("2025-08-18",200000,290,35,"2025-09-22","2025-10-13",5800,True,"2025-10",5800,0,""),
        ("2025-08-31",50000,300,35,"2025-10-05","2025-10-17",1500,True,"2025-10",1500,0,""),
        ("2025-08-31",200000,280,35,"2025-10-05","2025-10-20",5600,True,"2025-10",5600,0,""),
        ("2025-09-10",200000,280,35,"2025-10-15","2025-10-31",5600,True,"2025-10",5600,200,""),
        ("2025-09-10",50000,290,35,"2025-10-15","2025-10-30",1450,True,"2025-10",1450,0,"贴给老谭60000"),
        ("2025-09-12",200000,280,35,"2025-10-17","2025-11-06",5600,True,"2025-11",5600,0,"老谭贴我60000"),
        ("2025-09-22",200000,280,35,"2025-10-27","2025-11-14",5600,True,"2025-11",5600,0,""),
        ("2025-09-22",140000,280,35,"2025-10-27","2025-11-14",3920,True,"2025-11",3920,0,""),
        ("2025-09-30",200000,280,35,"2025-11-04","2025-11-21",5600,True,"2025-11",5600,0,""),
        ("2025-10-16",70000,270,35,"2025-11-20","2025-12-05",1890,True,"2025-12",1890,0,""),
        ("2025-10-16",200000,280,35,"2025-11-20","2025-12-09",5600,True,"2025-12",5600,0,""),
        ("2025-10-24",80000,280,35,"2025-11-28","2025-12-17",2240,True,"2025-12",1400,0,"有青山30000"),
        ("2025-10-24",200000,280,35,"2025-11-28","2025-12-19",5600,True,"2025-12",5600,0,""),
        ("2025-11-04",240000,290,35,"2025-12-09","2026-01-06",6960,True,"2026-01",6960,0,""),
        ("2025-11-08",300000,280,35,"2025-12-13","2026-01-15",8400,True,"2026-01",8400,0,""),
        ("2025-11-17",300000,280,35,"2025-12-22","2026-01-21",8400,True,"2026-01",8400,0,""),
        ("2025-11-27",300000,280,35,"2026-01-01","2026-02-02",8400,True,"2026-02",8400,0,""),
        ("2025-12-09",90000,280,35,"2026-01-13","2026-02-11",2520,True,"2026-02",2520,0,""),
        ("2025-12-10",300000,280,35,"2026-01-14","2026-03-06",8400,True,"2026-03",8400,200,""),
        ("2025-12-23",300000,280,35,"2026-01-27","2026-03-12",8400,True,"2026-03",8400,0,""),
        ("2026-01-09",300000,280,35,"2026-02-13","2026-03-24",8400,True,"2026-03",8400,0,""),
        ("2026-01-25",300000,280,35,"2026-03-01","2026-04-10",8400,True,"2026-04",8400,0,""),
        ("2026-01-26",300000,280,35,"2026-03-02","2026-04-17",8400,True,"2026-04",8400,200,""),
        ("2026-02-05",300000,290,35,"2026-03-12","2026-04-24",8700,True,"2026-04",8400,0,""),
        ("2026-02-12",200000,290,35,"2026-03-19","2026-05-08",5800,True,"2026-05",2900,0,"有青山10万"),
        ("2026-03-13",300000,280,35,"2026-04-17",None,8400,False,None,None,0,""),
        ("2026-03-14",300000,280,35,"2026-04-18",None,8400,False,None,None,0,""),
        ("2026-04-03",180000,280,35,"2026-05-08",None,5040,False,None,None,0,""),
        ("2026-04-13",220000,280,35,"2026-05-18",None,6160,False,None,None,0,""),
        ("2026-04-13",300000,280,35,"2026-05-18",None,8400,False,None,None,0,""),
        ("2026-04-21",300000,280,35,"2026-05-26",None,8400,False,None,None,0,"有青山5万"),
        ("2026-04-21",300000,280,35,"2026-05-26",None,8400,False,None,None,0,""),
    ]
    data = []
    for i, record in enumerate(rows, 1):
        data.append({
            'id': i,
            'date': record[0],
            'amount': record[1],
            'rate': record[2],
            'days': record[3],
            'returnDate': record[4],
            'actualDate': record[5],
            'interest': record[6],
            'returned': record[7],
            'returnMonth': record[8],
            'finalInterest': record[9],
            'toLaoTan': record[10],
            'remark': record[11],
        })
    return data


def load_legacy_data(data_file):
    if os.path.exists(data_file):
        with open(data_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return get_initial_data()


def import_records(conn, user_id, records):
    now = datetime.now().isoformat(timespec='seconds')
    for record in records:
        partner_name, partner_amount = parse_partner_fields(record)
        conn.execute(
            '''
            INSERT INTO records (
                user_id, date, amount, rate, days, return_date, actual_date,
                interest, returned, return_month, final_interest, service_fee,
                remark, partner_name, partner_amount, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (
                user_id,
                record.get('date', ''),
                int(record.get('amount', 0)),
                int(record.get('rate', 0)),
                int(record.get('days', 0)),
                record.get('returnDate', ''),
                record.get('actualDate'),
                int(record.get('interest', 0)),
                1 if record.get('returned') else 0,
                record.get('returnMonth'),
                record.get('finalInterest'),
                int(record.get('serviceFee', record.get('toLaoTan', 0)) or 0),
                record.get('remark', ''),
                partner_name,
                partner_amount,
                now,
                now,
            )
        )


def init_db(get_conn, config, data_file, password_hasher):
    seeded = False
    with get_conn() as conn:
        ensure_schema(conn)
        user_count = conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]
        if user_count == 0:
            seeded = True
            created_at = datetime.now().isoformat(timespec='seconds')
            legacy_hash = config.get('password_hash') or password_hasher('admin123')
            cur = conn.execute(
                'INSERT INTO users (username, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?)',
                ('admin', legacy_hash, 1, created_at)
            )
            import_records(conn, cur.lastrowid, load_legacy_data(data_file))
        conn.execute(
            'UPDATE users SET is_admin = 1 WHERE username = ?',
            ('admin',)
        )
        rows = conn.execute(
            '''
            SELECT id, amount, remark, partner_name, partner_amount
            FROM records
            '''
        ).fetchall()
        for row in rows:
            if row['partner_name'] or (row['partner_amount'] or 0):
                continue
            partner_name, partner_amount = parse_partner_fields({
                'amount': row['amount'],
                'remark': row['remark'],
            })
            if partner_name or partner_amount:
                conn.execute(
                    'UPDATE records SET partner_name = ?, partner_amount = ? WHERE id = ?',
                    (partner_name, partner_amount, row['id'])
                )
    return seeded


def ensure_schema(conn):
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            is_admin INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        )
        '''
    )
    user_columns = {row['name'] for row in conn.execute('PRAGMA table_info(users)').fetchall()}
    if 'is_admin' not in user_columns:
        conn.execute("ALTER TABLE users ADD COLUMN is_admin INTEGER NOT NULL DEFAULT 0")
    conn.execute(
        '''
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            date TEXT NOT NULL,
            amount INTEGER NOT NULL,
            rate INTEGER NOT NULL,
            days INTEGER NOT NULL,
            return_date TEXT,
            actual_date TEXT,
            interest INTEGER NOT NULL,
            returned INTEGER NOT NULL DEFAULT 0,
            return_month TEXT,
            final_interest INTEGER,
            service_fee INTEGER NOT NULL DEFAULT 0,
            remark TEXT NOT NULL DEFAULT '',
            partner_name TEXT NOT NULL DEFAULT '',
            partner_amount INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        '''
    )
    columns = {row['name'] for row in conn.execute('PRAGMA table_info(records)').fetchall()}
    if 'partner_name' not in columns:
        conn.execute("ALTER TABLE records ADD COLUMN partner_name TEXT NOT NULL DEFAULT ''")
    if 'partner_amount' not in columns:
        conn.execute("ALTER TABLE records ADD COLUMN partner_amount INTEGER NOT NULL DEFAULT 0")


def serialize_record(row):
    return {
        'id': row['id'],
        'date': row['date'],
        'amount': row['amount'],
        'rate': row['rate'],
        'days': row['days'],
        'returnDate': row['return_date'],
        'actualDate': row['actual_date'],
        'interest': row['interest'],
        'returned': bool(row['returned']),
        'returnMonth': row['return_month'],
        'finalInterest': row['final_interest'],
        'toLaoTan': row['service_fee'],
        'serviceFee': row['service_fee'],
        'partnerName': row['partner_name'],
        'partnerAmount': row['partner_amount'],
        'remark': row['remark'],
    }


def get_user_by_username(conn, username):
    return conn.execute(
        'SELECT id, username, password_hash, is_admin, created_at FROM users WHERE username = ?',
        ((username or '').strip(),)
    ).fetchone()


def get_records_for_user(conn, user_id):
    rows = conn.execute(
        '''
        SELECT id, date, amount, rate, days, return_date, actual_date, interest,
               returned, return_month, final_interest, service_fee, remark,
               partner_name, partner_amount
        FROM records
        WHERE user_id = ?
        ORDER BY date DESC, id DESC
        ''',
        (user_id,)
    ).fetchall()
    return [serialize_record(row) for row in rows]


def get_record_list_for_user(conn, user_id, filter_type='all', search='', sort_key='date', sort_dir='desc', page=1, page_size=15):
    where_clauses = ['user_id = ?']
    params = [user_id]

    if filter_type == 'returned':
        where_clauses.append('returned = 1')
    elif filter_type == 'pending':
        where_clauses.append('returned = 0')

    search = (search or '').strip()
    if search:
        where_clauses.append('(remark LIKE ? OR partner_name LIKE ? OR date LIKE ?)')
        like = f'%{search}%'
        params.extend([like, like, like])

    sort_map = {
        'date': 'date',
        'amount': 'amount',
        'rate': 'rate',
        'returnDate': 'return_date',
        'actualDate': 'actual_date',
        'interest': 'interest',
    }
    order_column = sort_map.get(sort_key, 'date')
    order_dir = 'ASC' if str(sort_dir).lower() == 'asc' else 'DESC'
    try:
        page = max(int(page or 1), 1)
    except (TypeError, ValueError):
        page = 1
    try:
        page_size = min(max(int(page_size or 15), 1), 100)
    except (TypeError, ValueError):
        page_size = 15

    where_sql = ' AND '.join(where_clauses)
    total = conn.execute(
        f'SELECT COUNT(*) FROM records WHERE {where_sql}',
        params
    ).fetchone()[0]
    total_pages = max((total + page_size - 1) // page_size, 1)
    if page > total_pages:
        page = total_pages
    offset = (page - 1) * page_size

    rows = conn.execute(
        f'''
        SELECT id, date, amount, rate, days, return_date, actual_date, interest,
               returned, return_month, final_interest, service_fee, remark,
               partner_name, partner_amount
        FROM records
        WHERE {where_sql}
        ORDER BY {order_column} {order_dir}, id DESC
        LIMIT ? OFFSET ?
        ''',
        params + [page_size, offset]
    ).fetchall()
    return {
        'items': [serialize_record(row) for row in rows],
        'total': total,
        'page': page,
        'pageSize': page_size,
        'totalPages': total_pages,
        'filter': filter_type,
        'search': search,
        'sort': {'key': sort_key, 'dir': order_dir.lower()},
    }


def get_record_row(conn, user_id, rid):
    return conn.execute(
        '''
        SELECT id, user_id, date, amount, rate, days, return_date, actual_date,
               interest, returned, return_month, final_interest, service_fee, remark,
               partner_name, partner_amount
        FROM records
        WHERE id = ? AND user_id = ?
        ''',
        (rid, user_id)
    ).fetchone()
