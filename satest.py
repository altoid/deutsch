# sqlalchemy futzing

import sqlalchemy
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql.expression import *

DSN='mysql://german:saurkraut@localhost:3306/deutsch?charset=utf8'
engine = sqlalchemy.create_engine(DSN)
engine.echo = True
conn = engine.connect()

db_metadata = sqlalchemy.MetaData(engine)

table_attribute       = sqlalchemy.Table('attribute', db_metadata, autoload=True)
table_word            = sqlalchemy.Table('word', db_metadata, autoload=True)
table_word_attributes = sqlalchemy.Table('word_attributes', db_metadata, autoload=True)
table_quiz            = sqlalchemy.Table('quiz', db_metadata, autoload=True)
table_quiz_structure  = sqlalchemy.Table('quiz_structure', db_metadata, autoload=True)

@compiles(Insert)
def xappend_string(insert, compiler, **kw):
    s = compiler.visit_insert(insert, **kw)
    if 'xappend_string' in insert.kwargs:
        return s + " " + insert.kwargs['xappend_string']
    return s

d = [
    { 'attribute_id' : 1,
      'word_id' : 49,
      'value' : 'xxDIS' },
    { 'attribute_id' : 3,
      'word_id' : 49,
      'value' : 'BxxLATTS' },
    { 'attribute_id' : 5,
      'word_id' : 49,
      'value' : 'STxxUFF' }
    ]

s = table_word_attributes.insert(xappend_string = 'ON DUPLICATE KEY UPDATE value=VALUES(value)')

print str(s)

conn.execute(s, d)

# select * from word where word is not null
#s = select([table_word]).where(isnot(null()))
