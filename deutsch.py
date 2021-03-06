from flask import Flask, session, request, url_for, escape, redirect, render_template, flash
import dtconfig
import sqlalchemy
import random
from sqlalchemy.sql.expression import *
from sqlalchemy.ext.compiler import compiles

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

table_attribute       = sqlalchemy.Table('attribute', db_metadata, autoload=True)
table_word            = sqlalchemy.Table('word', db_metadata, autoload=True)
table_word_attributes = sqlalchemy.Table('word_attributes', db_metadata, autoload=True)
table_quiz            = sqlalchemy.Table('quiz', db_metadata, autoload=True)
table_quiz_structure  = sqlalchemy.Table('quiz_structure', db_metadata, autoload=True)
table_quiz_score      = sqlalchemy.Table('quiz_score', db_metadata, autoload=True)

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

    return my_render_template('mainmenu.html')

def word_exists(conn, word, pos_id):

    s = select([table_word]).where(and_(table_word.c.word == word, table_word.c.pos_id == int(pos_id)))
    result = conn.execute(s)

    c = 0
    word_id = 0
    for row in result:
        word_id = row[table_word.c.id]
        c += 1

    if c == 0:
        return

    s = select([table_attribute, table_word_attributes]). \
        where(and_(table_attribute.c.id == table_word_attributes.c.attribute_id,
                   table_word_attributes.c.word_id == word_id))
    result = conn.execute(s)
    d = {}
    for row in result:
        d[row[table_attribute.c.attrkey] + '_attribute_key'] = row[table_word_attributes.c.value]
        d[row[table_attribute.c.attrkey] + '_attribute_id'] = row[table_word_attributes.c.attribute_id]

    d['word'] = word
    d['word_id'] = word_id

    return d

def add_word_to_db(conn, form, pos_id):

    # form is the filled-in form.  we need to pull out values for:
    #
    # pos_id
    # word
    # *_attribute_id

    word = form.get('word')
    attr_values = [x[1] for x in form.items() if x[0].endswith('_attribute_key')]
    attr_names = [x[0] for x in form.items() if x[0].endswith('_attribute_key')]
    suffix_len = len('_attribute_key')
    attr_names = [x[:-suffix_len] for x in attr_names]
    attr_ids = [x[1] for x in form.items() if x[0].endswith('_attribute_id')]

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

@compiles(Insert)
def append_string(insert, compiler, **kw):
    # cf. http://stackoverflow.com/questions/6611563/sqlalchemy-on-duplicate-key-update.
    # the keyword passed to the insert method has to be the same as the method.  if we call the keyword 'zuchinni,'
    # then this function has to be called zucchini too.

    s = compiler.visit_insert(insert, **kw)
    if 'append_string' in insert.kwargs:
        return s + " " + insert.kwargs['append_string']
    return s

def update_word(conn, form):

    # form has the current values plus whatever the user did to them

    suffix_len = len('_attribute_key')
    attr_names = [x[0][:-suffix_len] for x in form.items() if x[0].endswith('_attribute_key')]

    update_values = []
    word_id = form.get('word_id')
    for attr_name in attr_names:
        new_value = form.get('%s_attribute_key' % attr_name)
        attribute_id = int(form.get('%s_attribute_id' % attr_name))
        d = {
            'attribute_id' : attribute_id,
            'word_id' : word_id,
            'value' : new_value # could be none, that's ok
            }
        update_values.append(d)
    
    '''
    update word_attributes set value = newvalue where word_id = x and attribute_id = y
    '''
    
    s = table_word_attributes.insert(append_string = 'ON DUPLICATE KEY UPDATE value=VALUES(value)')
    conn.execute(s, update_values)

def get_pos_rows(conn):

    q = 'select id, name from pos'
    result = conn.execute(q)
    return result

def get_pos_attributes(conn, pos_id):

    # returns raw DB rows that contain the attribute names that will
    # be displayed on the add word form.

    q = '''
select pos_form.attribute_id, attribute.attrkey, pos.name
from pos_form, attribute, pos
where pos_form.attribute_id = attribute.id
and pos.id = pos_form.pos_id
and pos.id = %s
''' % pos_id

    result = conn.execute(q)
    attr_list = []
    final_result = {}
    for row in result:
        final_result['pos_name'] = row['name']
        attr_list.append({
                'id' : row['attribute_id'],
                'attrkey' : row['attrkey']
                })

    final_result['attr_list'] = attr_list
    return final_result

@app.route('/addword/<pos_id>', methods=['GET', 'POST'])
def addword(pos_id):

    with conn.begin():
        word_info = None
        template_to_render = 'addword.html'
        if request.method == 'POST':
            word = request.form.get('word', None)
            if not word:
                flash('Erk.  Type a word.')
            else:
                word_info = word_exists(conn, word, pos_id)
                if word_info:
                    # check that the word isn't already there
                    flash('"%s" is already there' % word)
                    template_to_render = 'updateword.html'
                else:
                    word_id = add_word_to_db(conn, request.form, pos_id)
                    flash('"%s" added to dictionary, id = %s' % (word, str(word_id)))
    
        # this fetches the attribute names that will be displayed on the add word form.
        attribute_info = get_pos_attributes(conn, pos_id)
    
        pos_rows = get_pos_rows(conn)
    
        return my_render_template(template_to_render,
                                  attribute_info=attribute_info,
                                  pos_id=pos_id,
                                  word_info=word_info,
                                  pos_rows=pos_rows)

@app.route('/updateword', methods=['POST'])
def updateword():

    with conn.begin():
        update_word(conn, request.form)
    
        pos_id = request.form.get('pos_id')
    
        # this fetches the attribute names that will be displayed on the add word form.
        attribute_info = get_pos_attributes(conn, pos_id)
    
        pos_rows = get_pos_rows(conn)
        flash('"%s" updated' % request.form.get('word'))
        return my_render_template('addword.html',
                                  attribute_info=attribute_info,
                                  pos_id=pos_id,
                                  pos_rows=pos_rows)

@app.route('/config')
def showconfig():

    return my_render_template('showconfig.html')

def get_quiz_list(conn):

    q = 'select id, name from quiz'
    result = conn.execute(q)
    d = []
    for row in result:
        d.append( {
                'id' : row['id'],
                'name' : row['name']
                })

    return d

@app.route('/quizzes')
def showquizzes():

    quiz_list = get_quiz_list(conn)

    return my_render_template('quizlist.html',
                              quiz_list=quiz_list)

def select_word_never_presented(quiz_id):

    sql = '''
select word.id from word
inner join quiz_structure
   on word.pos_id = quiz_structure.pos_id 
   and quiz_structure.quiz_id = %s
left join quiz_score 
   on quiz_structure.quiz_id = quiz_score.quiz_id
   and word.id = quiz_score.word_id
where quiz_score.last_presentation is null
order by rand()
limit 1
''' % (quiz_id)

    result = conn.execute(sql)

    row = result.first()
    if row:
        return row['id']

def select_word_few_presentations(quiz_id):

    sql = '''
select word.id from word
inner join quiz_structure
on word.pos_id = quiz_structure.pos_id and quiz_structure.quiz_id = %s
inner join quiz_score on quiz_structure.quiz_id = quiz_score.quiz_id and word.id = quiz_score.word_id
where presentation_count < 5
order by rand()
limit 1
''' % (quiz_id)

    result = conn.execute(sql)

    row = result.first()
    if row:
        return row['id']

def select_next_word(quiz_id):

    # select the next word.  this query guarantees that
    # the selected word has defined values for all the attributes
    # tested by the quiz.

    sql = '''
select word_id from quiz_word_attr_count qwac
inner join quiz_attr_count qac on qwac.quiz_id = qac.quiz_id
and qwac.pos_id = qac.pos_id
and qwac.attribute_id = qac.attribute_id
and qwac.attrcount = qac.attrcount
where qac.quiz_id = %s
''' % (quiz_id)

    candidate_word_ids = []
    result = conn.execute(sql)

    for row in result:
        candidate_word_ids.append(row['word_id'])

    return random.choice(candidate_word_ids)

def get_quiz_question_data(conn, quiz_id):

    # return a json object containing all the info we need to present the next quiz question.
    #
    # {
    #    quiz_id : <quiz_id>,
    #    word_id : <word_id>,
    #    attributes : [
    #         { key : <key1>, id : <id1> },
    #         { key : <key2>, id : <id2> }, ...
    #    ]
    # }

    # get all the attribute ids that are associated with this quiz.  then select
    # a word that has values for all the attribute ids.

    sql = '''
select distinct attribute.id, attribute.attrkey
 from quiz_structure, attribute
 where attribute_id = attribute.id and quiz_id = %s
''' % (quiz_id)

    result = conn.execute(sql)

    returnMe = {}
    returnMe['quiz_id'] = quiz_id
    attributes = []

    for row in result:
        d = {
            'key' : row['attrkey'],
            'id' : row['id'] 
            }

        attributes.append(d)

    returnMe['attributes'] = attributes

    word_id = select_next_word(quiz_id)

    returnMe['word_id'] = word_id

    return returnMe

def get_score(conn, quiz_id, word_id):

    sql = '''
select sum(correct_count) / sum(presentation_count) score
from quiz_score where quiz_id = %s
and word_id = %s
''' % (quiz_id, word_id)

    result = conn.execute(sql)
    row = result.first()

    if row['score'] is None:
        return None

    return float(row['score'])

def get_quintile(score):

    if score is None:
        return 'untested'

    if score < 0.20:
        return 'fifth'

    if score < 0.40:
        return 'fourth'

    if score < 0.60:
        return 'third'

    if score < 0.80:
        return 'fourth'

    return 'first'

def present_quiz_page(quiz_data):

    # select * from quiz where quiz_id = <quiz_id>
    sql = '''select name from quiz where id = %s''' % quiz_data['quiz_id']

    result = conn.execute(sql)
    row = result.fetchone()
    quiz_name=row['name']

    sql = '''select word from word where id = %s''' % quiz_data['word_id']

    result = conn.execute(sql)
    row = result.first()
    word = row['word']

    quintile = get_quintile(get_score(conn, quiz_data['quiz_id'], quiz_data['word_id']))

    quiz_list = get_quiz_list(conn)

    return my_render_template('showquiz.html',
                              quiz_name=quiz_name,
                              word=word,
                              quintile=quintile,
                              quiz_data=quiz_data,
                              quiz_list=quiz_list)

@app.route('/quizzes/<quiz_id>', methods=(['GET', 'POST']))
def take_quiz(quiz_id):

    quiz_data = get_quiz_question_data(conn, quiz_id)

    return present_quiz_page(quiz_data)

@app.route('/quizzes/<quiz_id>/exact/<word_id>', methods=(['POST']))
def receive_answer(quiz_id, word_id):

    # get all the answers submitted in the form

    suffix = '_attribute_key'
    suffix_len = len(suffix)

    attr_keys = [x[0][:-suffix_len] for x in request.form.items() if x[0].endswith('_attribute_key')]

    my_answers = {}
    keys_to_ids = {}
    for k in attr_keys:
        my_answers[k] = request.form.get(k + '_attribute_key').lower().strip()
        keys_to_ids[k] = request.form.get(k + '_attribute_id').strip()

    # get the correct answers from the database

    with conn.begin():
        sql = '''
select a.id, a.attrkey, wa.value
 from word_attributes wa,
 quiz_structure qs,
 attribute a
 where wa.word_id = %s
 and qs.quiz_id = %s
 and qs.attribute_id = wa.attribute_id
 and a.id = wa.attribute_id
''' % (word_id, quiz_id)

        result = conn.execute(sql)
        correct_answers = {}
        for row in result:
            correct_answers[row['attrkey']] = row['value']

        correct_scores = []
        incorrect_scores = []
        for k in attr_keys:
            if my_answers[k] == correct_answers[k]:

                d = {
                    'quiz_id' : quiz_id,
                    'word_id' : word_id,
                    'attribute_id' : keys_to_ids[k],
                    'presentation_count' : 1,
                    'correct_count' : 1
                }

                correct_scores.append(d)
            else:
                d = {
                    'quiz_id' : quiz_id,
                    'word_id' : word_id,
                    'attribute_id' : keys_to_ids[k],
                    'presentation_count' : 1
                }

                incorrect_scores.append(d)


        if len(correct_scores) > 0:
            correct_update_clause = 'on duplicate key update presentation_count = presentation_count + 1, correct_count = correct_count + 1'
            s = table_quiz_score.insert(append_string=correct_update_clause)
            conn.execute(s, correct_scores)
                
        if len(incorrect_scores) > 0:
            incorrect_update_clause = 'on duplicate key update presentation_count = presentation_count + 1'
            s = table_quiz_score.insert(append_string=incorrect_update_clause)
            conn.execute(s, incorrect_scores)
                
    return my_render_template('gradequiz.html',
                              quiz_id=quiz_id,
                              attr_keys=attr_keys,
                              my_answers=my_answers,
                              quiz_list=get_quiz_list(conn),
                              correct_answers=correct_answers)

@app.route('/showpos')
def showpos():

    pos_rows = get_pos_rows(conn)

    return my_render_template('showpos.html',
                              pos_rows=pos_rows)

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

