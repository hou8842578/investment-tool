import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

import app as app_module
from init_production_db import initialize_production_database


class InvestmentApiTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)
        self.original_db_file = app_module.DB_FILE

        app_module.DB_FILE = str(self.temp_path / 'test.db')
        data_file = self.temp_path / 'data.json'
        data_file.write_text('[]', encoding='utf-8')
        app_module.init_db(
            app_module.get_conn,
            {'password_hash': app_module.hash_password('admin123')},
            str(data_file),
            app_module.hash_password,
        )

        app_module.app.config['TESTING'] = True
        self.client = app_module.app.test_client()

    def tearDown(self):
        app_module.DB_FILE = self.original_db_file
        self.temp_dir.cleanup()

    def register_and_login(self, username='tester01', password='demo1234'):
        response = self.client.post('/api/register', json={
            'username': username,
            'password': password,
        })
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['username'], username)
        return username, password

    def create_record(self, **overrides):
        body = {
            'date': '2026-05-15',
            'amount': 120000,
            'rate': 300,
            'days': 30,
            'interest': 3600,
            'returnDate': '2026-06-14',
            'remark': '自动化测试',
            'partnerName': '合作方A',
            'partnerAmount': 20000,
        }
        body.update(overrides)
        response = self.client.post('/api/records', json=body)
        self.assertEqual(response.status_code, 200)
        return response.get_json()['id'], body

    def test_auth_flow(self):
        username, password = self.register_and_login(username='authcase', password='demo1234')

        status_response = self.client.get('/api/check-auth')
        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(status_response.get_json(), {
            'logged_in': True,
            'username': username,
            'is_admin': False,
        })

        change_response = self.client.post('/api/change-password', json={
            'old_password': password,
            'new_password': 'demo5678',
        })
        self.assertEqual(change_response.status_code, 200)
        self.assertTrue(change_response.get_json()['ok'])

        self.client.post('/api/logout')
        login_response = self.client.post('/api/login', json={
            'username': username,
            'password': 'demo5678',
        })
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.get_json()['ok'])

    def test_record_crud_and_dashboard_flow(self):
        self.register_and_login(username='recordcase', password='demo1234')
        record_id, record_body = self.create_record()

        list_response = self.client.get(
            '/api/records?filter=all&search=%E5%90%88%E4%BD%9C%E6%96%B9A&sortKey=amount&sortDir=desc&page=1&pageSize=10'
        )
        self.assertEqual(list_response.status_code, 200)
        list_payload = list_response.get_json()
        self.assertEqual(list_payload['total'], 1)
        self.assertEqual(list_payload['items'][0]['id'], record_id)

        update_response = self.client.put(f'/api/records/{record_id}', json={
            **record_body,
            'amount': 150000,
            'interest': 4500,
            'partnerAmount': 30000,
        })
        self.assertEqual(update_response.status_code, 200)

        return_response = self.client.post(f'/api/records/{record_id}/return', json={
            'actualDate': '2026-06-20',
            'finalInterest': 4300,
            'serviceFee': 200,
            'returnMonth': '2026-06',
        })
        self.assertEqual(return_response.status_code, 200)

        dashboard_response = self.client.get('/api/dashboard')
        self.assertEqual(dashboard_response.status_code, 200)
        dashboard = dashboard_response.get_json()
        self.assertEqual(dashboard['summary']['totalCount'], 1)
        self.assertEqual(dashboard['summary']['returnedCount'], 1)
        self.assertEqual(dashboard['summary']['totalInvested'], 150000)
        self.assertEqual(dashboard['summary']['myInvested'], 120000)
        self.assertEqual(dashboard['summary']['receivedInterest'], 4300)
        self.assertEqual(dashboard['summary']['myReceivedInterest'], 3440)
        self.assertEqual(dashboard['partners'][0]['name'], '合作方A')
        self.assertEqual(dashboard['partners'][0]['amount'], 30000)
        self.assertAlmostEqual(dashboard['partners'][0]['annualizedYield'], 29.06, places=2)
        self.assertEqual(dashboard['yearly'][0]['myFinalInterest'], 3440)
        self.assertEqual(dashboard['monthlyInterest'][0]['month'], '2026-06')
        self.assertEqual(dashboard['monthlyInterest'][0]['myValue'], 3440)

        delete_response = self.client.delete(f'/api/records/{record_id}')
        self.assertEqual(delete_response.status_code, 200)
        final_list_response = self.client.get('/api/records?filter=all&page=1&pageSize=10')
        self.assertEqual(final_list_response.get_json()['total'], 0)

    def test_export_endpoints(self):
        self.register_and_login(username='exportcase', password='demo1234')
        self.create_record(remark='导出测试')

        json_response = self.client.get('/api/export')
        self.assertEqual(json_response.status_code, 200)
        self.assertIn('application/json', json_response.headers['Content-Type'])
        exported_json = json.loads(json_response.data.decode('utf-8'))
        self.assertEqual(exported_json[0]['remark'], '导出测试')

        excel_response = self.client.get('/api/export/excel')
        self.assertEqual(excel_response.status_code, 200)
        self.assertTrue(
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in excel_response.headers['Content-Type']
            or 'text/csv' in excel_response.headers['Content-Type']
        )

    def test_init_production_db_script(self):
        prod_db = self.temp_path / 'production' / 'app.db'
        prod_config = self.temp_path / 'production' / 'config.json'

        result = initialize_production_database(
            db_file=str(prod_db),
            config_file=str(prod_config),
            admin_username='prodadmin',
            admin_password='prod5678',
            secret_key='demo-secret',
            force=False,
        )

        self.assertEqual(result['admin_username'], 'prodadmin')
        self.assertTrue(prod_db.exists())
        self.assertTrue(prod_config.exists())

        config = json.loads(prod_config.read_text(encoding='utf-8'))
        self.assertEqual(config['secret_key'], 'demo-secret')
        self.assertEqual(config['initialized_for'], 'production')

        conn = sqlite3.connect(str(prod_db))
        conn.row_factory = sqlite3.Row
        try:
            user = conn.execute(
                'SELECT username, is_admin FROM users WHERE username = ?',
                ('prodadmin',)
            ).fetchone()
            self.assertIsNotNone(user)
            self.assertEqual(user['username'], 'prodadmin')
            self.assertEqual(user['is_admin'], 1)
            record_count = conn.execute('SELECT COUNT(*) FROM records').fetchone()[0]
            self.assertEqual(record_count, 0)
        finally:
            conn.close()

    def test_admin_endpoints_and_password_reset(self):
        login_response = self.client.post('/api/login', json={
            'username': 'admin',
            'password': 'admin123',
        })
        self.assertEqual(login_response.status_code, 200)
        self.assertTrue(login_response.get_json()['is_admin'])

        overview_response = self.client.get('/api/admin/overview')
        self.assertEqual(overview_response.status_code, 200)
        overview = overview_response.get_json()
        self.assertEqual(overview['totalUsers'], 1)
        self.assertEqual(overview['adminUsers'], 1)
        self.assertIn('activeUsers30d', overview)
        self.assertIn('returnedRate', overview)
        self.assertIn('rankings', overview)

        self.client.post('/api/logout')
        self.register_and_login(username='normaluser', password='demo1234')
        record_id, record_body = self.create_record(
            amount=100000,
            interest=3000,
            rate=300,
            partnerName='合作方B',
            partnerAmount=10000,
        )
        self.client.post(f'/api/records/{record_id}/return', json={
            'actualDate': '2026-06-18',
            'finalInterest': 2800,
            'serviceFee': 100,
            'returnMonth': '2026-06',
        })

        forbidden_response = self.client.get('/api/admin/users')
        self.assertEqual(forbidden_response.status_code, 403)

        self.client.post('/api/logout')
        self.client.post('/api/login', json={
            'username': 'admin',
            'password': 'admin123',
        })
        users_response = self.client.get('/api/admin/users')
        self.assertEqual(users_response.status_code, 200)
        users = users_response.get_json()['items']
        target_user = next(u for u in users if u['username'] == 'normaluser')
        self.assertFalse(target_user['isAdmin'])
        self.assertEqual(target_user['recordCount'], 1)
        self.assertEqual(target_user['returnRate'], 100.0)
        self.assertEqual(target_user['avgRate'], 300.0)
        self.assertGreaterEqual(target_user['avgActualDays'], 30.0)
        self.assertIn(target_user['activityLevel'], ['活跃', '一般', '沉寂'])

        overview_after_response = self.client.get('/api/admin/overview')
        overview_after = overview_after_response.get_json()
        self.assertGreaterEqual(overview_after['activeUsers30d'], 1)
        self.assertTrue(any(item['username'] == 'normaluser' for item in overview_after['rankings']['topInvested']))

        reset_response = self.client.post(
            f"/api/admin/users/{target_user['id']}/reset-password",
            json={'newPassword': 'reset5678'},
        )
        self.assertEqual(reset_response.status_code, 200)
        self.assertTrue(reset_response.get_json()['ok'])

        self.client.post('/api/logout')
        relogin_response = self.client.post('/api/login', json={
            'username': 'normaluser',
            'password': 'reset5678',
        })
        self.assertEqual(relogin_response.status_code, 200)
        self.assertTrue(relogin_response.get_json()['ok'])


if __name__ == '__main__':
    unittest.main()
