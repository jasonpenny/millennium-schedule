import os
import sqlite3
import sys
from extract_appt import extract_appt_days, days_of_week

def _get_db_cursor_with_table():
    conn = sqlite3.connect('appts.db')
    c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS appts(dt, seq, time, who, what);')
    conn.commit()
    return conn

def save_appts(days):
    conn = _get_db_cursor_with_table()
    c = conn.cursor()

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

def _main():
    h = os.environ.get('SCHED_HOST')
    u = os.environ.get('SCHED_USER')
    p = os.environ.get('SCHED_PASS')

    if not h or not u or not p:
        print '$SCHED_HOST and $SCHED_USER and $SCHED_PASS must be defined'
        sys.exit(1)

    save_appts(extract_appt_days(h, u, p))

if __name__ == '__main__':
    _main()
