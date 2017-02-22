from flask_server import app, request, session, redirect, render_template
from extract_appt import extract_appt_days, days_of_week

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        session['host'] = request.form['host']
        session['user'] = request.form['user']
        session['pass'] = request.form['pass']
        return redirect('/')

    if session.get('user'):
        days = extract_appt_days(session['host'],
                                 session['user'],
                                 session['pass'])
        return render_template('logged_in_index.html',
                               days_of_week=days_of_week(),
                               days=days)

    return app.send_static_file('index.html')

@app.route('/logout')
def logout():
    session.pop('host', None)
    session.pop('user', None)
    session.pop('pass', None)
    return redirect('/')
