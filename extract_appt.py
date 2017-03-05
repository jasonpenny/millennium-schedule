from collections import deque
import copy
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

def extract_appt_days(host, user, password):
    s = requests.Session()
    r = s.get('http://{}/login.asp'.format(host))

    if 'RemoteBusiness - Login' in r.text:
        login_data = {
            'login': user,
            'Password': password
        }
        r = s.post('http://{}/login.asp'.format(host), data=login_data)

    r = s.get('http://{}/employee/empappbook.asp'.format(host))
    bs = BeautifulSoup(r.text, 'html.parser')

    tbl = bs.find('table', {'class': 'AppBook'})
    days = {daynum: {'start': None, 'end': None, 'appts': []} for daynum in range(7)}
    time_filled = {daynum: [] for daynum in range(7)}

    rows = tbl.find_all('tr')
    try:
        start_td = rows[1].find('td')
        start_time = int(start_td.contents[0][:2])
        curr_time = QuarterHour(start_time, 0)
    except ValueError:
        curr_time = QuarterHour(10, 0)

    for tr in rows[1:]:
        tds = deque(tr.find_all('td')[1:])
        for daynum in range(7):
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

    return days

def output_days(days):
    for daynum, dayname in days_of_week():
        if days[daynum]['appts']:
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

    output_days(extract_appt_days(h, u, p))

if __name__ == '__main__':
    _main()
