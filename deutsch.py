from flask import Flask, session, request, url_for, escape, redirect, render_template, flash
import dtconfig
import sqlalchemy
import pprint
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

table_attribute = sqlalchemy.Table('attribute', db_metadata, autoload=True)
table_word = sqlalchemy.Table('word', db_metadata, autoload=True)
table_word_attributes = sqlalchemy.Table('word_attributes', db_metadata, autoload=True)

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

    with conn.begin():
        s = sqlalchemy.select([table_word]).where(and_(table_word.c.word == word, table_word.c.pos_id == int(pos_id)))
        result = conn.execute(s)

        c = 0
        word_id = 0
        for row in result:
            print row
            word_id = row[table_word.c.id]
            c += 1

        if c == 0:
            return

        s = sqlalchemy.select([table_attribute, table_word_attributes]). \
            where(and_(table_attribute.c.id == table_word_attributes.c.attribute_id,
                       table_word_attributes.c.word_id == word_id))
        result = conn.execute(s)
        d = {}
        for row in result:
            print row
            d[row[table_attribute.c.attrkey] + '_attribute_key'] = row[table_word_attributes.c.value]
            d[row[table_attribute.c.attrkey] + '_attribute_id'] = row[table_word_attributes.c.attribute_id]

        d['word'] = word
        d['word_id'] = word_id

        print pprint.pformat(d)

        return d

def add_word_to_db(form):

    # form is the filled-in form.  we need to pull out values for:
    #
    # pos_id
    # word
    # *_attribute_id

    global conn

    pos_id = form.get('pos_id')
    word = form.get('word')
    attr_values = [x[1] for x in form.items() if x[0].endswith('_attribute_key')]
    attr_names = [x[0] for x in form.items() if x[0].endswith('_attribute_key')]
    suffix_len = len('_attribute_key')
    attr_names = [x[:-suffix_len] for x in attr_names]
    attr_ids = [x[1] for x in form.items() if x[0].endswith('_attribute_id')]

    with conn.begin():  # this is how transactions are done with sqlalchemy
        s = table_word.insert()
        result = conn.execute(s, word=word, pos_id=pos_id)

        pklist = result.inserted_primary_key
        word_id = pklist[0]

        attrs_to_insert = []
        for attr_name in attr_names:
            attr_value = form.get('%s_attribute_key' % attr_name)
            if attr_value:
                d = {
                    'attribute_id' : form.get('%s_attribute_id' % attr_name),
                    'word_id' : word_id,
                    'value' : attr_value
                    }
                attrs_to_insert.append(d)

        if len(attrs_to_insert) > 0:
            result = conn.execute(table_word_attributes.insert(), attrs_to_insert)

        return word_id

def update_word(form):

    # form has the current values plus whatever the user did to them
    
    suffix_len = len('_attribute_key')
    attr_names = [x[0][:-suffix_len] for x in form.items() if x[0].endswith('_attribute_key')]

    update_values = []
    word_id = form.get('word_id')
    for attr_name in attr_names:
        old_value = form.get('%s_attribute_key' % attr_name)
        new_value = form.get('%s_attribute_key' % attr_name)
        attribute_id = int(form.get('%s_attribute_id' % attr_name))
        d = {
            'c_attribute_id' : attribute_id,
            'newvalue' : new_value # could be none, that's ok
            }
        update_values.append(d)
    
    '''
    update word_attributes set value = newvalue where word_id = x and attribute_id = y
    '''
    
    with conn.begin():
        stmt = table_word_attributes.update().\
            where(and_(table_word_attributes.c.word_id == word_id,
                       table_word_attributes.c.attribute_id == sqlalchemy.bindparam('c_attribute_id'))).\
                       values(value=sqlalchemy.bindparam('newvalue'))
        conn.execute(stmt, update_values)

@app.route('/addword', methods=['GET', 'POST'])
def addword():
    global conn

    pos_id = None
    word_info = None
    template_to_render = 'addword.html'
    if request.method == 'POST':
        pos_id = request.form['pos_id']
        word = request.form.get('word', None)
        if not word:
            flash('Erk.  Type a word.')
        else:
            word_info = word_exists(word, pos_id)
            if word_info:
                # check that the word isn't already there
                flash('"%s" is already there' % word)
                template_to_render = 'updateword.html'
            else:
                word_id = add_word_to_db(request.form)
                flash('"%s" added to dictionary, id = %s' % (word, str(word_id)))

    else:
        pos_id = request.args.get('pos_id')

    # this fetches the attribute names that will be displayed on the add word form.
    q = '''
select pos_form.attribute_id, attribute.attrkey
from pos_form, attribute
where pos_form.attribute_id = attribute.id
and pos_form.pos_id = %s
''' % pos_id

    attribute_info = conn.execute(q)

    username=escape(session['username'])
    return render_template(template_to_render,
                           username=username,
                           attribute_info=attribute_info,
                           pos_id=pos_id,
                           word_info=word_info,
                           logout_url=url_for('logout'))

@app.route('/updateword', methods=['POST'])
def updateword():

    update_word(request.form)

    pos_id = request.form.get('pos_id')

    # this fetches the attribute names that will be displayed on the add word form.
    q = '''
select pos_form.attribute_id, attribute.attrkey
from pos_form, attribute
where pos_form.attribute_id = attribute.id
and pos_form.pos_id = %s
''' % pos_id

    attribute_info = conn.execute(q)

    statusmessage = '"%s" updated' % request.form.get('word')
    username=escape(session['username'])
    return render_template('addword.html',
                           username=username,
                           attribute_info=attribute_info,
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

