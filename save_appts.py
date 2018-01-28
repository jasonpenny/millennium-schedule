from datetime import datetime
import os
import sqlite3
import sys
from icalendar import Calendar, Event
from extract_appt import extract_two_appt_days, days_of_week

def _get_db_cursor_with_table():
    conn = sqlite3.connect('appts.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS appts(dt, seq, time, who, what);')
    conn.commit()
    return conn

def save_appts(tuple_of_days):
    conn = _get_db_cursor_with_table()
    c = conn.cursor()

    for days in tuple_of_days:
        for daynum, _ in days_of_week():
            if days[daynum]['appts']:
                dt = days[daynum]['date'].strftime('%Y-%m-%d')

                c.execute('DELETE FROM appts WHERE dt = ?', (dt,))

                for i, appt in enumerate(days[daynum]['appts']):
                    c.execute(
                        'INSERT INTO appts (dt, seq, time, who, what) '
                        'VALUES (?, ?, ?, ?, ?);',
                        (dt, i + 1, appt['time'], appt['who'], appt.get('what', ''))
                    )

    conn.commit()
    conn.close()

def output_ical():
    conn = _get_db_cursor_with_table()
    c = conn.cursor()

    cal = Calendar()
    cal.add('prodid', '-//Work Appointments//sched.jasontpenny.com//')
    cal.add('name', 'Work Appointments')
    cal.add('x-wr-calname', 'Work Appointmens')

    sql = 'SELECT * FROM appts'
    for row in c.execute(sql):
        dt, _, time, who, what = row

        start, end = time.split(' - ')
        dtstart = datetime.strptime(dt + ' ' + start, '%Y-%m-%d %I:%M%p')
        dtend = datetime.strptime(dt + ' ' + end, '%Y-%m-%d %I:%M%p')
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

    if not h or not u or not p:
        print '$SCHED_HOST and $SCHED_USER and $SCHED_PASS must be defined'
        sys.exit(1)

    save_appts(extract_two_appt_days(h, u, p))

    output_ical()

if __name__ == '__main__':
    _main()
