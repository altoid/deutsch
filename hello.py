from flask import Flask, session, request, url_for, escape, redirect, render_template

app = Flask(__name__)
app.secret_key = 'no one will ever guess this'

@app.route('/')
def index():
    if 'username' not in session:
        return redirect(url_for('login'))

    username=escape(session['username'])
    if not username:
        return redirect(url_for('login'))

    return render_template('ack.html', 
                           username=escape(session['username']),
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

