from flask import Flask, g, jsonify, request, session, redirect, \
        render_template
from flask_session import Session

app = Flask(__name__)
app.config.from_object('server_config')
Session(app)

import flask_server.views
