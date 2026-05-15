import csv
import io
import json
from datetime import date

from flask import send_file


EXPORT_HEADERS = ['ID', '投资日期', '投资金额', '利息/万', '天数', '计划回款', '实际回款', '利息总额', '已回款', '回款月份', '最终利息', '服务费', '合作方', '合作出资', '备注']


def build_export_rows(records):
    return [[
        record['id'],
        record['date'],
        record['amount'],
        record['rate'],
        record['days'],
        record['returnDate'],
        record.get('actualDate') or '',
        record['interest'],
        '是' if record['returned'] else '否',
        record.get('returnMonth') or '',
        record.get('finalInterest') or '',
        record.get('serviceFee', 0),
        record.get('partnerName', ''),
        record.get('partnerAmount', 0),
        record.get('remark', '')
    ] for record in records]


def export_json_response(records, username):
    payload = json.dumps(records, ensure_ascii=False, indent=2).encode('utf-8')
    return send_file(
        io.BytesIO(payload),
        as_attachment=True,
        download_name=f'投资记录_{username}_{date.today().isoformat()}.json',
        mimetype='application/json'
    )


def export_excel_or_csv_response(records, username, has_excel, workbook_cls=None):
    rows = build_export_rows(records)
    if has_excel and workbook_cls:
        workbook = workbook_cls()
        worksheet = workbook.active
        worksheet.title = '投资记录'
        worksheet.append(EXPORT_HEADERS)
        for row in rows:
            worksheet.append(row)
        for col in worksheet.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            worksheet.column_dimensions[col[0].column_letter].width = min(max_len + 4, 30)
        buf = io.BytesIO()
        workbook.save(buf)
        buf.seek(0)
        return send_file(
            buf,
            as_attachment=True,
            download_name=f'投资记录_{username}_{date.today().isoformat()}.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(EXPORT_HEADERS)
    for row in rows:
        writer.writerow(row)
    buf = io.BytesIO(output.getvalue().encode('utf-8-sig'))
    return send_file(
        buf,
        as_attachment=True,
        download_name=f'投资记录_{username}_{date.today().isoformat()}.csv',
        mimetype='text/csv'
    )
