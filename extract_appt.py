from collections import deque
import copy
from datetime import datetime, timedelta
import os
import sys
import requests
from bs4 import BeautifulSoup

class QuarterHour(object):
    def __init__(self, h, m):
        self.h = h
        self.m = m

    def inc(self):
        self.m += 15
        if self.m > 45:
            self.h += 1
            self.m = 0

    def after(self, inc_amount):
        result = QuarterHour(self.h, self.m)
        while inc_amount:
            result.inc()
            inc_amount -= 1
        return result

    def fill_time(self, filled, inc_amount):
        tmp = QuarterHour(self.h, self.m)
        while inc_amount:
            filled.append(unicode(tmp))
            tmp.inc()
            inc_amount -= 1

    def __repr__(self):
        h = self.h
        md = 'am' if h < 12 else 'pm'
        if h > 12:
            h -= 12
        return '{0}:{1:02d}{2}'.format(h, self.m, md)

def extract_text(tag):
    result = ''
    if tag and tag.contents and tag.contents[0]:
        for tc in tag.contents:
            in_tag = False
            for c in unicode(tc).replace('<br>', '\n'):
                if c in ['<', '>']:
                    in_tag = not in_tag
                    continue

                if not in_tag:
                    result += c
    return [line for line in result.split('\n') if line != u'\xa0']

def days_of_week():
    return [(0, 'Sunday'),
            (1, 'Monday'),
            (2, 'Tuesday'),
            (3, 'Wednesday'),
            (4, 'Thursday'),
            (5, 'Friday'),
            (6, 'Saturday')]

def setup_requests_session(host, user, password):
    s = requests.Session()
    r = s.get('http://{}/login.asp'.format(host))

    if 'RemoteBusiness - Login' in r.text:
        login_data = {
            'login': user,
            'Password': password
        }
        s.post('http://{}/login.asp'.format(host), data=login_data)

    return s

def extract_appt_days(host, user, password):
    s = setup_requests_session(host, user, password)

    r = s.get('http://{}/employee/empappbook.asp'.format(host))
    days, _ = extract_appt_days_from_request(r)
    return days

def extract_four_appt_days(host, user, password):
    s = setup_requests_session(host, user, password)

    r = s.get('http://{}/employee/empappbook.asp'.format(host))
    days, next_date = extract_appt_days_from_request(r)

    result = [days]
    for _ in range(3):
        r = s.post('http://{}/employee/empappbook.asp'.format(host),
                   data={'date': next_date.strftime('%m/%d/%Y'), 'submit': 'Go'})
        next_days, next_date = extract_appt_days_from_request(r)
        result.append(next_days)

    return tuple(result)

def extract_appt_days_from_request(r):
    bs = BeautifulSoup(r.text, 'html.parser')

    tbl = bs.find('table', {'class': 'AppBook'})
    days = {daynum: {'start': None, 'end': None, 'appts': []} for daynum in range(7)}
    time_filled = {daynum: [] for daynum in range(7)}

    rows = tbl.find_all('tr')
    try:
        start_date_td = rows[0].find('td').next_sibling.next_sibling
        start_date_txt = start_date_td.contents[1].get_text()
        start_date = datetime.strptime(start_date_txt, '%m/%d/%Y')
        start_td = rows[1].find('td')
        start_time = int(start_td.contents[0][:2])
        curr_time = QuarterHour(start_time, 0)
    except ValueError:
        curr_time = QuarterHour(10, 0)

    for tr in rows[1:]:
        tds = deque(tr.find_all('td')[1:])
        loop_date = start_date
        for daynum in range(7):
            days[daynum]['date'] = loop_date
            loop_date = loop_date + timedelta(days=1)

            if not tds:
                break

            if unicode(curr_time) not in time_filled[daynum]:
                td = tds.popleft()

                if td and td.contents:
                    cell = unicode(td.contents[0])
                    if not days[daynum]['start'] and cell != u'<OFF>':
                        days[daynum]['start'] = copy.copy(curr_time)
                    elif days[daynum]['start'] and not days[daynum]['end'] and cell == u'<OFF>':
                        days[daynum]['end'] = copy.copy(curr_time)

                if td.get('class') and u'AppBookOn' in td['class']:
                    appt_text = extract_text(td)
                    try:
                        appt_len = int(td.get('rowspan'))
                    except TypeError:
                        appt_len = 1
                    appt_time = copy.copy(curr_time)

                    days[daynum]['appts'].append({
                        'time': '{} - {}'.format(appt_time, appt_time.after(appt_len)),
                        'who': appt_text[1],
                        'what': appt_text[2] if len(appt_text) > 2 else '',
                    })

                    appt_time.fill_time(time_filled[daynum], appt_len)

        curr_time.inc()

    return days, loop_date

def output_days(days):
    for daynum, dayname in days_of_week():
        if days[daynum]['appts']:
            print days[daynum]['date']
            print '{} [{} - {}]'.format(
                dayname, days[daynum]['start'], days[daynum]['end'])
            for appt in days[daynum]['appts']:
                print '    ' + appt['time']
                print '        ' + appt['who']
                if appt['what']:
                    print '        ' + appt['what']
                print ''

def _main():
    h = os.environ.get('SCHED_HOST')
    u = os.environ.get('SCHED_USER')
    p = os.environ.get('SCHED_PASS')

    if not h or not u or not p:
        print '$SCHED_HOST and $SCHED_USER and $SCHED_PASS must be defined'
        sys.exit(1)

    tuple_of_days = extract_four_appt_days(h, u, p)
    for days in tuple_of_days:
        output_days(days)

if __name__ == '__main__':
    _main()
