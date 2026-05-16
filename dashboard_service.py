from datetime import date


def calc_days_between(start_date, end_date):
    if not start_date or not end_date:
        return None
    try:
        return max((date.fromisoformat(end_date) - date.fromisoformat(start_date)).days, 0)
    except ValueError:
        return None


def get_partner_amount(record):
    return max(int(record.get('partnerAmount') or 0), 0)


def get_my_amount(record):
    amount = int(record.get('amount') or 0)
    return max(amount - get_partner_amount(record), 0)


def split_interest(total_interest, record):
    amount = int(record.get('amount') or 0)
    partner_amount = get_partner_amount(record)
    total_interest = total_interest or 0
    if amount <= 0 or partner_amount <= 0 or total_interest == 0:
        return total_interest, 0
    partner_interest = round(total_interest * partner_amount / amount)
    return total_interest - partner_interest, partner_interest


def build_dashboard_summary(records):
    total_invested = sum(r['amount'] for r in records)
    my_invested = sum(get_my_amount(r) for r in records)
    pending_amount = sum(r['amount'] for r in records if not r['returned'])
    my_pending_amount = sum(get_my_amount(r) for r in records if not r['returned'])
    received_interest = sum((r.get('finalInterest') or 0) for r in records if r['returned'])
    my_received_interest = sum(split_interest(r.get('finalInterest') or 0, r)[0] for r in records if r['returned'])
    pending_interest = sum(r['interest'] for r in records if not r['returned'])
    my_pending_interest = sum(split_interest(r['interest'], r)[0] for r in records if not r['returned'])
    returned_count = sum(1 for r in records if r['returned'])
    total_count = len(records)
    avg_rate = round(sum(r['rate'] for r in records) / total_count) if total_count else 0
    actual_days = [
        calc_days_between(r['date'], r.get('actualDate'))
        for r in records if r.get('actualDate')
    ]
    actual_days = [d for d in actual_days if d is not None]
    avg_days = round(sum(actual_days) / len(actual_days)) if actual_days else 0
    return {
        'totalInvested': total_invested,
        'myInvested': my_invested,
        'pendingAmount': pending_amount,
        'myPendingAmount': my_pending_amount,
        'receivedInterest': received_interest,
        'myReceivedInterest': my_received_interest,
        'pendingInterest': pending_interest,
        'myPendingInterest': my_pending_interest,
        'returnedCount': returned_count,
        'totalCount': total_count,
        'returnRate': round(returned_count / total_count * 100) if total_count else 0,
        'avgRate': avg_rate,
        'avgDays': avg_days,
    }


def build_yearly_summary(records):
    year_map = {}
    for record in records:
        year = record['date'][:4]
        if year not in year_map:
            year_map[year] = {
                'year': year,
                'invested': 0,
                'myInvested': 0,
                'count': 0,
                'returnedCount': 0,
                'finalInterest': 0,
                'myFinalInterest': 0,
                'serviceFee': 0,
                'capitalDays': 0,
                'myCapitalDays': 0,
            }
        bucket = year_map[year]
        bucket['invested'] += record['amount']
        bucket['myInvested'] += get_my_amount(record)
        bucket['count'] += 1
        if record['returned']:
            bucket['returnedCount'] += 1
            bucket['finalInterest'] += record.get('finalInterest') or 0
            bucket['myFinalInterest'] += split_interest(record.get('finalInterest') or 0, record)[0]
            bucket['serviceFee'] += record.get('serviceFee') or 0
            actual_days = calc_days_between(record['date'], record.get('actualDate'))
            if actual_days is not None:
                bucket['capitalDays'] += record['amount'] * actual_days
                bucket['myCapitalDays'] += get_my_amount(record) * actual_days

    result = []
    for year in sorted(year_map.keys(), reverse=True):
        item = year_map[year]
        capital_days = item.pop('capitalDays')
        my_capital_days = item.pop('myCapitalDays')
        item['annualizedYield'] = round(item['finalInterest'] * 36500 / capital_days, 2) if capital_days > 0 else 0
        item['myAnnualizedYield'] = round(item['myFinalInterest'] * 36500 / my_capital_days, 2) if my_capital_days > 0 else 0
        result.append(item)
    return result


def build_partner_summary(records):
    partner_map = {}
    total_amount = sum(r['amount'] for r in records)
    total_interest = sum((r.get('finalInterest') or 0) for r in records if r['returned'])
    for record in records:
        partner_name = (record.get('partnerName') or '').strip()
        partner_amount = int(record.get('partnerAmount') or 0)
        if not partner_name or partner_amount <= 0:
            continue
        if partner_name not in partner_map:
            partner_map[partner_name] = {
                'name': partner_name,
                'amount': 0,
                'interest': 0,
                'count': 0,
                'capitalDays': 0,
            }
        bucket = partner_map[partner_name]
        bucket['amount'] += partner_amount
        bucket['count'] += 1
        if record['returned'] and record.get('finalInterest'):
            bucket['interest'] += split_interest(record.get('finalInterest') or 0, record)[1]
            actual_days = calc_days_between(record['date'], record.get('actualDate'))
            if actual_days is not None:
                bucket['capitalDays'] += partner_amount * actual_days

    result = []
    for name in sorted(partner_map.keys()):
        item = partner_map[name]
        capital_days = item.pop('capitalDays')
        item['myAmount'] = total_amount - item['amount']
        item['myInterest'] = total_interest - item['interest']
        item['annualizedYield'] = round(item['interest'] * 36500 / capital_days, 2) if capital_days > 0 else 0
        result.append(item)
    return result


def build_alerts(records):
    urgent = []
    near = []
    for record in records:
        if record['returned'] or not record.get('returnDate'):
            continue
        try:
            days_left = (date.fromisoformat(record['returnDate']) - date.today()).days
        except ValueError:
            continue
        item = {
            'id': record['id'],
            'date': record['date'],
            'amount': record['amount'],
            'returnDate': record['returnDate'],
            'daysLeft': days_left,
        }
        if days_left < 0:
            urgent.append(item)
        elif days_left <= 3:
            near.append(item)
    return {'urgent': urgent, 'near': near}


def build_monthly_interest(records):
    month_map = {}
    for record in records:
        month = record.get('returnMonth')
        if not month:
            continue
        if month not in month_map:
            month_map[month] = {'value': 0, 'myValue': 0}
        total_interest = record.get('finalInterest') or 0
        my_interest, _ = split_interest(total_interest, record)
        month_map[month]['value'] += total_interest
        month_map[month]['myValue'] += my_interest
    return [
        {'month': month, 'value': month_map[month]['value'], 'myValue': month_map[month]['myValue']}
        for month in sorted(month_map.keys())
    ]


def build_days_trend(records):
    month_map = {}
    for record in records:
        month = record.get('returnMonth')
        actual_date = record.get('actualDate')
        if not month or not actual_date:
            continue
        actual_days = calc_days_between(record['date'], actual_date)
        if actual_days is None:
            continue
        if month not in month_map:
            month_map[month] = {'planSum': 0, 'actualSum': 0, 'count': 0}
        month_map[month]['planSum'] += record.get('days') or 0
        month_map[month]['actualSum'] += actual_days
        month_map[month]['count'] += 1
    result = []
    for month in sorted(month_map.keys()):
        item = month_map[month]
        result.append({
            'month': month,
            'planAvg': round(item['planSum'] / item['count']) if item['count'] else 0,
            'actualAvg': round(item['actualSum'] / item['count']) if item['count'] else 0,
        })
    return result


def build_rate_trend(records):
    month_map = {}
    for record in records:
        month = record.get('returnMonth')
        actual_date = record.get('actualDate')
        if not month or not actual_date:
            continue
        if month not in month_map:
            month_map[month] = {'rateSum': 0, 'count': 0}
        month_map[month]['rateSum'] += record['rate']
        month_map[month]['count'] += 1
    result = []
    for month in sorted(month_map.keys()):
        item = month_map[month]
        result.append({
            'month': month,
            'avgRate': round(item['rateSum'] / item['count']) if item['count'] else 0,
        })
    return result


def build_dashboard_payload(records):
    return {
        'alerts': build_alerts(records),
        'summary': build_dashboard_summary(records),
        'monthlyInterest': build_monthly_interest(records),
        'daysTrend': build_days_trend(records),
        'rateTrend': build_rate_trend(records),
        'yearly': build_yearly_summary(records),
        'partners': build_partner_summary(records),
    }
