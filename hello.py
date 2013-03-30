from flask import Flask, session, request, url_for, escape, redirect, render_template
import dtconfig
import sqlalchemy
from sqlalchemy.sql import and_, or_, not_

#
# for some bizarre reason, you can't use from_pyfile
# to import any user-defined variables.  the only variables
# that could be set with from_pyfile are the ones well-known
# to flask.  
#
# however, when using from_object, it was possible to inject
# user-defined variables into the config.
#

# cf http://www.rmunn.com/sqlalchemy-tutorial/tutorial.html

app = Flask(__name__)
app.config.from_object('dtconfig.DTConfig')

engine = sqlalchemy.create_engine(app.config['DSN'])
engine.echo = True
conn = engine.connect()

db_metadata = sqlalchemy.MetaData(engine)

table_word = sqlalchemy.Table('word', db_metadata, autoload=True)

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

def word_exists(word, pos_id):

    global conn
    global table_word

    s = sqlalchemy.select([table_word]).where(and_(table_word.c.word == word, table_word.c.pos_id == int(pos_id)))
    result = conn.execute(s)

    c = 0
    for row in result:
        c += 1

    return c > 0

def add_word_to_db(word, pos_id):

    global conn
    global table_word

    s = table_word.insert()
    result = conn.execute(s, word=word, pos_id=pos_id)

    return result.inserted_primary_key

@app.route('/addword', methods=['GET', 'POST'])
def addword():
    global conn

    pos_id=None
    if request.method == 'POST':
        pos_id = request.form['pos_id']
        word = request.form.get('word', None)
        if not word:
            statusmessage = 'Erk.  Type a word.'
        elif word_exists(word, pos_id):
            # check that the word isn't already there
            statusmessage = '"%s" is already there' % word
        else:
            word_id = add_word_to_db(word, pos_id)
            statusmessage = '"%s" added to dictionary, id = %s' % (word, str(word_id))

        statusmessage += str(request.form)

    else:
        pos_id = request.args.get('pos_id')
        statusmessage = None

    q = '''
select pos_form.attribute_id, attribute.name 
from pos_form, attribute
where pos_form.attribute_id = attribute.id
and pos_form.pos_id = %s
''' % pos_id

    result = conn.execute(q)

    username=escape(session['username'])
    return render_template('addword.html',
                           username=username,
                           result=result,
                           statusmessage=statusmessage,
                           pos_id=pos_id,
                           logout_url=url_for('logout'))

@app.route('/showconfig')
def showconfig():
    username=escape(session['username'])
    return render_template('showconfig.html',
                           username=username,
                           logout_url=url_for('logout'))

@app.route('/showpos')
def showpos():

    q = 'select id, name from pos'
    result = conn.execute(q)

    username=escape(session['username'])
    return render_template('showpos.html',
                           username=username,
                           result=result,
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

