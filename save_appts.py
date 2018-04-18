from datetime import datetime, timedelta
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

                c.execute('DELETE FROM appts WHERE dt = ?', (dt,))
                day_appts = gcal_events_for_day(events, cal_id, dt)

                for i, appt in enumerate(days[daynum]['appts']):
                    summary = appt['who']
                    if appt.get('what'):
                        summary += ', ' + appt['what']
                    start, end = appt['time'].split(' - ')
                    dtstart = datetime.strptime(dt + ' ' + start, '%Y-%m-%d %I:%M%p')
                    dtend = datetime.strptime(dt + ' ' + end, '%Y-%m-%d %I:%M%p')

                    key = u'{}|{}'.format(appt['time'], summary)
                    if key in day_appts:
                        # Event exists with the same info
                        c.execute(
                            'INSERT INTO appts (dt, seq, time, who, what, eventid) '
                            'VALUES (?, ?, ?, ?, ?, ?);',
                            (dt, i + 1, appt['time'], appt['who'], appt.get('what', ''), day_appts[key])
                        )
                        del day_appts[key]
                        continue

                    # Event doesn't exist yet, put it in google calendar
                    event = gcal.add_event(events, cal_id, summary, dtstart, dtend)

                    c.execute(
                        'INSERT INTO appts (dt, seq, time, who, what, eventid) '
                        'VALUES (?, ?, ?, ?, ?, ?);',
                        (dt, i + 1, appt['time'], appt['who'], appt.get('what', ''), event['id'])
                    )

                if day_appts.keys():
                    for eventid in day_appts.values():
                        gcal.delete_event(events, cal_id, eventid)

    conn.commit()
    conn.close()

def date_str_to_time_str(s):
    dt = datetime.strptime(s, '%Y-%m-%dT%H:%M')
    result = dt.strftime('%I:%M%p').lower()
    if result[0] == '0':
        return result[1:]

    return result

def gcal_events_for_day(events, cal_id, search_date):
    start_date = datetime.strptime(search_date, '%Y-%m-%d')
    end_date = start_date \
            + timedelta(days=1) \
            - timedelta(minutes=1)
    time_min = start_date \
            .replace(tzinfo=pytz.timezone('America/New_York')).isoformat('T')
    time_max = end_date \
            .replace(tzinfo=pytz.timezone('America/New_York')).isoformat('T')

    result = {}
    pageToken = ''
    while True:
        eventlist = events.list(calendarId=cal_id,
                                pageToken=pageToken,
                                timeMin=time_min,
                                timeMax=time_max).execute()
        for ev in eventlist['items']:
            start = date_str_to_time_str(ev['start']['dateTime'][:16])
            end = date_str_to_time_str(ev['end']['dateTime'][:16])

            time = '{} - {}'.format(start, end)

            what = ev['summary']
            key = u'{}|{}'.format(time, what)
            result[key] = ev['id']

        pageToken = eventlist.get('nextPageToken', '')
        if pageToken == '':
            break

    return result

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
