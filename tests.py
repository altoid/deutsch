import pprint
import dtconfig
import sqlalchemy
from sqlalchemy.sql.expression import *
from sqlalchemy.ext.compiler import compiles

import unittest
import deutsch

class TestDeutsch(unittest.TestCase):

    @classmethod
    def setUpClass(cls):

        cls.engine = sqlalchemy.create_engine(dtconfig.DTConfig.DSN)
        cls.engine.echo = True
        cls.conn = cls.engine.connect()
        
        db_metadata = sqlalchemy.MetaData(cls.engine)
        
        cls.table_attribute       = sqlalchemy.Table('attribute', db_metadata, autoload=True)
        cls.table_word            = sqlalchemy.Table('word', db_metadata, autoload=True)
        cls.table_word_attributes = sqlalchemy.Table('word_attributes', db_metadata, autoload=True)
        cls.table_quiz            = sqlalchemy.Table('quiz', db_metadata, autoload=True)
        cls.table_quiz_structure  = sqlalchemy.Table('quiz_structure', db_metadata, autoload=True)
        cls.table_quiz_score      = sqlalchemy.Table('quiz_score', db_metadata, autoload=True)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()

    def test_quizData(self):

        result = deutsch.get_quiz_question_data(self.conn, 2)

        print '\n%s' % (pprint.pformat(result))

if __name__ == '__main__':
    unittest.main()
