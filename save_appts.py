from datetime import datetime
import os
import sqlite3
import sys
import pytz
from icalendar import Calendar, Event
from extract_appt import extract_four_appt_days, days_of_week
import gcal

def _get_db_cursor_with_table():
    conn = sqlite3.connect('appts.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS appts(dt, seq, time, who, what, eventid);')
    conn.commit()
    return conn

def save_appts(tuple_of_days, cal_id):
    conn = _get_db_cursor_with_table()
    c = conn.cursor()
    events = gcal.service_events()

    for days in tuple_of_days:
        for daynum, _ in days_of_week():
            if days[daynum]['appts']:
                dt = days[daynum]['date'].strftime('%Y-%m-%d')

                sql = 'SELECT * FROM appts WHERE dt = ? ORDER BY seq'
                day_appts = {}
                for row in c.execute(sql, (dt,)):
                    dt, seq, time, who, what, eventid = row

                    key = u'{}-{}-{}'.format(time, who, what)
                    day_appts[key] = (seq, eventid)

                for i, appt in enumerate(days[daynum]['appts']):
                    key = u'{}-{}-{}'.format(appt['time'], appt['who'], appt.get('what', ''))
                    if key in day_appts:
                        # Event exists with the same info
                        del day_appts[key]
                        continue

                    summary = appt['who']
                    if appt.get('what'):
                        summary += ', ' + appt['what']
                    start, end = appt['time'].split(' - ')
                    dtstart = datetime.strptime(dt + ' ' + start, '%Y-%m-%d %I:%M%p')
                    dtend = datetime.strptime(dt + ' ' + end, '%Y-%m-%d %I:%M%p')

                    event = gcal.add_event(events, cal_id, summary, dtstart, dtend)

                    c.execute(
                        'INSERT INTO appts (dt, seq, time, who, what, eventid) '
                        'VALUES (?, ?, ?, ?, ?, ?);',
                        (dt, i + 1, appt['time'], appt['who'], appt.get('what', ''), event['id'])
                    )

                if day_appts.keys():
                    for seq, eventid in day_appts.values():
                        gcal.delete_event(events, cal_id, eventid)

                        c.execute(
                            'DELETE FROM appts WHERE dt = ? AND seq = ?',
                            (dt, seq)
                        )

    conn.commit()
    conn.close()

# deprecated, google only updates from ical urls a few times per day.
def output_ical():
    conn = _get_db_cursor_with_table()
    c = conn.cursor()

    NY = pytz.timezone('America/New_York')

    cal = Calendar()
    cal.add('prodid', '-//Work Appointments//sched.jasontpenny.com//')
    cal.add('name', 'Work Appointments')
    cal.add('x-wr-calname', 'Work Appointmens')

    sql = 'SELECT * FROM appts'
    for row in c.execute(sql):
        dt, _, time, who, what = row

        start, end = time.split(' - ')
        dtstart = datetime.strptime(dt + ' ' + start, '%Y-%m-%d %I:%M%p') \
                .replace(tzinfo=NY)
        dtend = datetime.strptime(dt + ' ' + end, '%Y-%m-%d %I:%M%p') \
                .replace(tzinfo=NY)

        summary = who
        if what:
            summary += ': ' + what

        event = Event()
        event.add('summary', summary)
        event.add('dtstart', dtstart)
        event.add('dtend', dtend)

        cal.add_component(event)

    with open('./flask_server/static/bc5fea56971f.ics', 'wb') as f:
        f.write(cal.to_ical())

def _main():
    h = os.environ.get('SCHED_HOST')
    u = os.environ.get('SCHED_USER')
    p = os.environ.get('SCHED_PASS')
    cal_id = os.environ.get('CALENDAR_ID')

    if not h or not u or not p:
        print '$SCHED_HOST and $SCHED_USER and $SCHED_PASS must be defined'
        sys.exit(1)

    save_appts(extract_four_appt_days(h, u, p), cal_id)

if __name__ == '__main__':
    _main()
