from flask import Flask, session, request, url_for, escape, redirect, render_template, flash
import dtconfig
import MySQLdb
import MySQLdb.cursors
import pprint
import random

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

conn = MySQLdb.connect(host=app.config['dbHOST'],
                       user=app.config['dbUSER'],
                       passwd=app.config['dbPASSWD'],
                       db=app.config['dbDATABASE'],
                       port=app.config['dbPORT'],
                       charset='utf8',
                       cursorclass=MySQLdb.cursors.SSCursor)

def my_render_template(template_name, **kwargs):

    if 'username' not in session:
        return redirect(url_for('login'))

    username=escape(session['username'])
    if not username:
        return redirect(url_for('login'))

    kwargs['username'] = username
    kwargs['logout_url'] = url_for('logout')

    return render_template(template_name, **kwargs)

@app.route('/')
def index():

    return my_render_template('base.html')

def word_exists(word, pos_id):

    c = MySQLdb.cursor()

    sql = '''select id, word from word where word = '%s' and pos_id = %s''' % (word, pos_id)

    c.execute(sql)

    row = c.fetchone()
    if not row:
        return

    word_id = row[0]
    word = row[1]

    # get the attribute ids, keys, and values for this word
    sql = '''
select a.id, a.attrkey, wa.value
from word_attributes wa, attribute a
where wa.attribute_id = a.id and wa.word_id = %s
''' % word_id

    c.execute(sql)
    d = {}
    for row in c.fetchall():
        attrkey = row[1]
        d[attrkey + '_attribute_key'] = row[2]
        d[attrkey + '_attribute_id'] = row[0]

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

    return my_render_template(template_to_render,
                              attribute_info=attribute_info,
                              pos_id=pos_id,
                              word_info=word_info)

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
    return my_render_template('addword.html',
                              attribute_info=attribute_info,
                              statusmessage=statusmessage,
                              pos_id=pos_id)

@app.route('/config')
def showconfig():

    return my_render_template('showconfig.html')

@app.route('/quizzes')
def showquizzes():

    q = 'select id, name from quiz'
    result = conn.execute(q)

    return my_render_template('quizlist.html',
                              result=result)

def select_next_word(quiz_id, pos_id):
    '''
    return the id of a word corresponding to the part of speech
    '''
    sql = 'select * from word where pos_id = %s order by rand() limit 1' % pos_id
    result = conn.execute(sql)

    row = result.first()
    if row is None:
        raise Exception('no words for pos_id %s (quiz %s)' % (pos_id, quiz_id))

    return row['id']

def get_quiz_question_data(quiz_id):
    '''
    return a tuple containing all the info we need to present the next quiz question.
    that tuple contains:

    (word_id, attribute_id)
    '''
    # 'select distinct quiz_id, attribute_id from quiz_structure where quiz_id = <quiz_id>'

    s = sqlalchemy.select([table_quiz_structure]).where(table_quiz_structure.c.quiz_id == quiz_id)
    result = conn.execute(s)

    # turn the result into a structure that looks like this:
    #
    # <attribute_id> => [pos_ids]
    #
    # i.e. take all the attribute_ids and map them to a list of all them matching parts of speech

    if not result.returns_rows:
        raise Exception('no such quiz id:  %s' % quiz_id)

    quiz_dict = {}
    for row in result:
        r = quiz_dict.get(row['attribute_id'])
        if not r:
            quiz_dict[row['attribute_id']] = [row['pos_id']]
        else:
            quiz_dict[row['attribute_id']].append(row['pos_id'])

    selected_attribute_id = random.choice(quiz_dict.keys())
    selected_pos_id = random.choice(quiz_dict[selected_attribute_id])

    # select a random word.  handle the case of no words defined for a part of speech
    # by showing an error message.

    word_id = select_next_word(quiz_id, selected_pos_id)

    # make sure there is a defined value for this attribute.  if not, return None

    s = sqlalchemy.select([table_word_attributes]).\
        where(and_(table_word_attributes.c.attribute_id == selected_attribute_id,
                   table_word_attributes.c.word_id == word_id))
    
    result = conn.execute(s)
    # result.returns_rows won't work - it will return True even if the query gives 0 rows

    row = result.first()
    if row is None:
        print '###################################### word_id = %s' % word_id
        return None

    word_id = row['word_id']
    print '*********************** word_id = %s' % word_id
    return (word_id, selected_attribute_id)

def present_quiz_page(quiz_id, word_id, attribute_id):

    # select * from quiz where quiz_id = <quiz_id>
    s = sqlalchemy.select([table_quiz]).where(table_quiz.c.id == quiz_id)

    result = conn.execute(s)
    row = result.fetchone()
    quiz_name=row['name']

    s = sqlalchemy.select([table_word]).where(table_word.c.id == word_id)

    result = conn.execute(s)
    row = result.first()
    word = row['word']

    s = sqlalchemy.select([table_attribute]).\
        where(table_attribute.c.id == attribute_id)

    result = conn.execute(s)
    row = result.first()
    attrkey = row['attrkey']

    return my_render_template('showquiz.html',
                              quiz_name=quiz_name,
                              quiz_id=quiz_id,
                              word=word,
                              word_id=word_id,
                              attrkey=attrkey,
                              attribute_id=attribute_id)

@app.route('/quizzes/<quiz_id>')
def take_quiz(quiz_id):

    while True:
        t = get_quiz_question_data(quiz_id)
        if t is not None:
            break

    word_id, attribute_id = t

    return present_quiz_page(quiz_id, word_id, attribute_id)

@app.route('/quizzes/<quiz_id>/exact', methods=(['POST']))
def receive_answer(quiz_id):

    # extract the submitted answer, compare to correct answer
    answer = request.form.get('response').strip().lower()
    word_id = request.form.get('word_id')
    attribute_id = request.form.get('attribute_id')

    if not answer:
        flash('type something, you idiot')
        return present_quiz_page(quiz_id, word_id, attribute_id)

    s = sqlalchemy.select([table_word_attributes]).\
        where(and_(table_word_attributes.c.attribute_id == attribute_id,
                   table_word_attributes.c.word_id == word_id))

    result = conn.execute(s)
    row = result.first()
    correct_answer = row['value'].lower()

    if correct_answer == answer:
        flash('that answer was correct')
    else:
        flash('nope, the correct answer is %s' % correct_answer)

    while True:
        t = get_quiz_question_data(quiz_id)
        if t is not None:
            break

    word_id, attribute_id = t
    return present_quiz_page(quiz_id, word_id, attribute_id)

@app.route('/showpos')
def showpos():

    q = 'select id, name from pos'
    result = conn.execute(q)

    return my_render_template('showpos.html',
                              result=result)

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

