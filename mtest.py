# MySQLdb futzing

import MySQLdb
import MySQLdb.cursors
import dtconfig

conn = MySQLdb.connect(host=dtconfig.DTConfig.dbHOST,
                       user=dtconfig.DTConfig.dbUSER,
                       passwd=dtconfig.DTConfig.dbPASSWD,
                       db=dtconfig.DTConfig.dbDATABASE,
                       port=dtconfig.DTConfig.dbPORT,
                       charset='utf8',
                       cursorclass=MySQLdb.cursors.SSCursor)

sql = '''
select * from word_attributes where word_id = %s
''' % ('49')

cursor = conn.cursor()
cursor.execute(sql)

for row in cursor.fetchall():
    print row
    print row['value']

