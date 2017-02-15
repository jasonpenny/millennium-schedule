from collections import deque
import copy
import os
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
        return '{0:2}:{1:02d}{2}'.format(h, self.m, md)

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

def day_of_week():
    return [(0, 'Sunday'),
            (1, 'Monday'),
            (2, 'Tuesday'),
            (3, 'Wednesday'),
            (4, 'Thursday'),
            (5, 'Friday'),
            (6, 'Saturday')]
s = requests.Session()
r = s.get('http://100.37.113.8/login.asp')

if 'RemoteBusiness - Login' in r.text:
    login_data = {
        'login': os.environ['SCHED_USER'],
        'Password': os.environ['SCHED_PASS']
    }
    r = s.post('http://100.37.113.8/login.asp', data=login_data)

r = s.get('http://100.37.113.8/employee/empappbook.asp')
bs = BeautifulSoup(r.text, 'html.parser')

tbl = bs.find('table', {'class': 'AppBook'})
days = {daynum: [] for daynum in range(7)}
time_filled = {daynum: [] for daynum in range(7)}

curr_time = QuarterHour(10, 0)
for tr in tbl.find_all('tr')[1:]:

    tds = deque(tr.find_all('td')[1:])
    for daynum in range(7):
        if not tds:
            break

        if unicode(curr_time) not in time_filled[daynum]:
            td = tds.popleft()

            if td.get('class') and u'AppBookOn' in td['class']:
                appt_text = extract_text(td)
                appt_len = int(td.get('rowspan'))
                appt_time = copy.copy(curr_time)

                days[daynum].append({
                    'time': '{} - {}'.format(appt_time, appt_time.after(appt_len)),
                    'who': appt_text[1],
                    'what': appt_text[2] if len(appt_text) > 2 else '',
                })

                appt_time.fill_time(time_filled[daynum], appt_len)

    curr_time.inc()

for daynum, dayname in day_of_week():
    if days[daynum]:
        print dayname
        for appt in days[daynum]:
            print '    ' + appt['time']
            print '        ' + appt['who']
            if appt['what']:
                print '        ' + appt['what']
            print ''
