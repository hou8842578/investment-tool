from auth_service import hash_password


def safe_pct(numerator, denominator):
    if not denominator:
        return 0
    return round(numerator * 100.0 / denominator, 2)


def activity_level(last_active_at):
    if not last_active_at:
        return '无数据'
    age_days = conn_days_since(last_active_at)
    if age_days <= 30:
        return '活跃'
    if age_days <= 90:
        return '一般'
    return '沉寂'


def conn_days_since(date_string):
    from datetime import datetime

    try:
        target = datetime.fromisoformat(str(date_string))
    except ValueError:
        return 9999
    delta = datetime.now() - target
    return delta.days


def build_admin_overview(conn):
    user_stats = conn.execute(
        '''
        SELECT
            COUNT(*) AS total_users,
            SUM(CASE WHEN is_admin = 1 THEN 1 ELSE 0 END) AS admin_users
        FROM users
        '''
    ).fetchone()
    record_stats = conn.execute(
        '''
        SELECT
            COUNT(*) AS total_records,
            COALESCE(SUM(amount), 0) AS total_invested,
            COALESCE(SUM(CASE WHEN returned = 0 THEN amount ELSE 0 END), 0) AS pending_amount,
            COALESCE(SUM(CASE WHEN returned = 1 THEN final_interest ELSE 0 END), 0) AS received_interest,
            SUM(CASE WHEN returned = 1 THEN 1 ELSE 0 END) AS returned_count,
            SUM(CASE WHEN returned = 0 THEN 1 ELSE 0 END) AS pending_count
        FROM records
        '''
    ).fetchone()
    latest_users = conn.execute(
        '''
        SELECT username, is_admin, created_at
        FROM users
        ORDER BY datetime(created_at) DESC, id DESC
        LIMIT 5
        '''
    ).fetchall()
    activity_stats = conn.execute(
        '''
        SELECT
            SUM(CASE WHEN last_active_at IS NOT NULL AND julianday('now') - julianday(last_active_at) <= 30 THEN 1 ELSE 0 END) AS active_users_30d,
            AVG(CASE WHEN record_count > 0 THEN record_count ELSE NULL END) AS avg_records_per_user
        FROM (
            SELECT
                u.id,
                COUNT(r.id) AS record_count,
                MAX(COALESCE(r.updated_at, r.created_at, u.created_at)) AS last_active_at
            FROM users u
            LEFT JOIN records r ON r.user_id = u.id
            GROUP BY u.id
        )
        '''
    ).fetchone()
    ranking_rows = conn.execute(
        '''
        SELECT
            u.username,
            COUNT(r.id) AS record_count,
            COALESCE(SUM(r.amount), 0) AS total_invested,
            COALESCE(SUM(CASE WHEN r.returned = 1 THEN r.final_interest ELSE 0 END), 0) AS received_interest,
            COALESCE(SUM(CASE WHEN r.returned = 0 THEN r.amount ELSE 0 END), 0) AS pending_amount
        FROM users u
        LEFT JOIN records r ON r.user_id = u.id
        GROUP BY u.id, u.username
        HAVING COUNT(r.id) > 0
        ORDER BY total_invested DESC, received_interest DESC, u.id DESC
        '''
    ).fetchall()
    top_invested = sorted(ranking_rows, key=lambda row: (row['total_invested'], row['received_interest']), reverse=True)[:5]
    top_interest = sorted(ranking_rows, key=lambda row: (row['received_interest'], row['total_invested']), reverse=True)[:5]
    top_pending = sorted(ranking_rows, key=lambda row: (row['pending_amount'], row['total_invested']), reverse=True)[:5]
    return {
        'totalUsers': user_stats['total_users'] or 0,
        'adminUsers': user_stats['admin_users'] or 0,
        'totalRecords': record_stats['total_records'] or 0,
        'totalInvested': record_stats['total_invested'] or 0,
        'pendingAmount': record_stats['pending_amount'] or 0,
        'receivedInterest': record_stats['received_interest'] or 0,
        'returnedCount': record_stats['returned_count'] or 0,
        'pendingCount': record_stats['pending_count'] or 0,
        'activeUsers30d': activity_stats['active_users_30d'] or 0,
        'avgRecordsPerUser': round(activity_stats['avg_records_per_user'] or 0, 1),
        'returnedRate': safe_pct(record_stats['returned_count'] or 0, record_stats['total_records'] or 0),
        'latestUsers': [
            {
                'username': row['username'],
                'isAdmin': bool(row['is_admin']),
                'createdAt': row['created_at'],
            }
            for row in latest_users
        ],
        'rankings': {
            'topInvested': [
                {
                    'username': row['username'],
                    'value': row['total_invested'] or 0,
                    'recordCount': row['record_count'] or 0,
                }
                for row in top_invested
            ],
            'topInterest': [
                {
                    'username': row['username'],
                    'value': row['received_interest'] or 0,
                    'recordCount': row['record_count'] or 0,
                }
                for row in top_interest
            ],
            'topPending': [
                {
                    'username': row['username'],
                    'value': row['pending_amount'] or 0,
                    'recordCount': row['record_count'] or 0,
                }
                for row in top_pending
            ],
        },
    }


def list_users_with_stats(conn):
    rows = conn.execute(
        '''
        SELECT
            u.id,
            u.username,
            u.is_admin,
            u.created_at,
            COUNT(r.id) AS record_count,
            COALESCE(SUM(r.amount), 0) AS total_invested,
            COALESCE(SUM(CASE WHEN r.returned = 0 THEN r.amount ELSE 0 END), 0) AS pending_amount,
            COALESCE(SUM(CASE WHEN r.returned = 1 THEN r.final_interest ELSE 0 END), 0) AS received_interest,
            COALESCE(AVG(CASE WHEN r.id IS NOT NULL THEN r.rate ELSE NULL END), 0) AS avg_rate,
            COALESCE(AVG(CASE WHEN r.returned = 1 AND r.actual_date IS NOT NULL THEN julianday(r.actual_date) - julianday(r.date) ELSE NULL END), 0) AS avg_actual_days,
            SUM(CASE WHEN r.returned = 1 THEN 1 ELSE 0 END) AS returned_count,
            SUM(CASE WHEN r.returned = 0 THEN 1 ELSE 0 END) AS pending_count,
            MAX(r.date) AS latest_invest_date,
            MAX(COALESCE(r.updated_at, r.created_at, u.created_at)) AS last_active_at
        FROM users u
        LEFT JOIN records r ON r.user_id = u.id
        GROUP BY u.id, u.username, u.is_admin, u.created_at
        ORDER BY total_invested DESC, received_interest DESC, u.id DESC
        '''
    ).fetchall()
    return [{
            'id': row['id'],
            'username': row['username'],
            'isAdmin': bool(row['is_admin']),
            'createdAt': row['created_at'],
            'recordCount': row['record_count'] or 0,
            'totalInvested': row['total_invested'] or 0,
            'pendingAmount': row['pending_amount'] or 0,
            'receivedInterest': row['received_interest'] or 0,
            'avgRate': round(row['avg_rate'] or 0, 1),
            'avgActualDays': round(row['avg_actual_days'] or 0, 1),
            'returnedCount': row['returned_count'] or 0,
            'pendingCount': row['pending_count'] or 0,
            'returnRate': safe_pct(row['returned_count'] or 0, row['record_count'] or 0),
            'latestInvestDate': row['latest_invest_date'],
            'lastActiveAt': row['last_active_at'],
            'activityLevel': activity_level(row['last_active_at']),
        }
        for row in rows]


def reset_user_password(conn, user_id, new_password, validate_password):
    err = validate_password(new_password)
    if err:
        return err, 400
    user = conn.execute(
        'SELECT id, username FROM users WHERE id = ?',
        (user_id,)
    ).fetchone()
    if not user:
        return '用户不存在', 404
    conn.execute(
        'UPDATE users SET password_hash = ? WHERE id = ?',
        (hash_password(new_password), user_id)
    )
    return None, 200
