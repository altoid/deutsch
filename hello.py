from flask import Flask, session, request, url_for, escape, redirect, render_template
import dtconfig
from sqlalchemy import create_engine

#
# for some bizarre reason, you can't use from_pyfile
# to import any user-defined variables.  the only variables
# that could be set with from_pyfile are the ones well-known
# to flask.  
#
# however, when using from_object, it was possible to inject
# user-defined variables into the config.
#

app = Flask(__name__)
app.config.from_object('dtconfig.DTConfig')

engine = create_engine(app.config['DSN'])
conn = engine.connect()

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    username=escape(session['username'])
    if not username:
        return redirect(url_for('login'))

    return render_template('base.html', 
                           username=username,
                           logout_url=url_for('logout'))

@app.route('/addword')
def addword():
    global conn
    q = 'select id, name from pos'
    result = conn.execute(q)
    
    username=escape(session['username'])
    return render_template('addword.html',
                           username=username,
                           result=result,
                           logout_url=url_for('logout'))

@app.route('/showconfig')
def showconfig():
    username=escape(session['username'])
    return render_template('showconfig.html',
                           username=username,
                           logout_url=url_for('logout'))

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():

    # action="" means redirect to the form the browser already has loaded.

    if request.method == 'GET':
        return render_template('login.html')

    session['username'] = request.form['username']
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')

