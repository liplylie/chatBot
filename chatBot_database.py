import sqlite3
import json
from datetime import datetime
from os.path import expanduser

home = expanduser("~")
dbName = 'RedditData'
timeframe = '2008-05'
sql_transaction = []
start_row = 0
cleanup = 100000


connection = sqlite3.connect('{}.db'.format(dbName))
c = connection.cursor()

# c.execute('DROP TABLE IF EXISTS parent_reply')

def create_table():
    c.execute("CREATE TABLE IF NOT EXISTS parent_reply(parent_id TEXT PRIMARY KEY, comment_id TEXT UNIQUE, parent TEXT, comment TEXT, subreddit TEXT, unix INT, score INT)")

def format_data(data):
    data = data.replace('\n',' newlinechar ').replace('\r',' newlinechar ').replace('"',"'")
    return data

def transaction_bldr(sql):
    global sql_transaction
    sql_transaction.append(sql)
    if len(sql_transaction) > 1000:
        c.execute('BEGIN TRANSACTION')
        for s in sql_transaction:
            try:
                c.execute(s)
            except:
                pass
        connection.commit()
        sql_transaction = []

def sql_insert_replace_comment(commentid,parentid,parent,comment,subreddit,time,score):
    try:
        sql = """UPDATE parent_reply SET parent_id = ?, comment_id = ?, parent = ?, comment = ?, subreddit = ?, unix = ?, score = ? WHERE parent_id =?;""".format(parentid, commentid, parent, comment, subreddit, int(time), score, parentid)
        transaction_bldr(sql)
    except Exception as e:
        print('s0 insert',str(e))

def sql_insert_has_parent(commentid,parentid,parent,comment,subreddit,time,score):
    try:
        sql = """INSERT INTO parent_reply (parent_id, comment_id, parent, comment, subreddit, unix, score) VALUES ("{}","{}","{}","{}","{}",{},{});""".format(parentid, commentid, parent, comment, subreddit, int(time), score)
        transaction_bldr(sql)
    except Exception as e:
        print('s0 has parent',str(e))

def sql_insert_no_parent(commentid,parentid,comment,subreddit,time,score):
    try:
        sql = """INSERT INTO parent_reply (parent_id, comment_id, comment, subreddit, unix, score) VALUES ("{}","{}","{}","{}",{},{});""".format(parentid, commentid, comment, subreddit, int(time), score)
        transaction_bldr(sql)
    except Exception as e:
        print('s0 no parent',str(e))

def acceptable(data):
    if len(data.split(' ')) > 1000 or len(data) < 1:
        return False
    elif len(data) > 32000:
        return False
    elif data == '[deleted]':
        return False
    elif data == '[removed]':
        return False
    else:
        return True

def find_parent(pid):
    try:
        sql = "SELECT comment FROM parent_reply WHERE comment_id = '{}' LIMIT 1".format(pid)
        c.execute(sql)
        result = c.fetchone()
        if result != None:
            return result[0]
        else: return False
    except Exception as e:
        #print(str(e))
        return False

def find_existing_score(pid):
    try:
        sql = "SELECT score FROM parent_reply WHERE parent_id = '{}' LIMIT 1".format(pid)
        c.execute(sql)
        result = c.fetchone()
        if result != None:
            return result[0]
        else: return False
    except Exception as e:
        #print(str(e))
        return False
    
if __name__ == '__main__':
    create_table()
    row_counter = 0
    paired_rows = 0

    with open("{}/Desktop/chatBot/RC_{}".format(home, timeframe), buffering=1000) as f:
        for row in f:
            row_counter += 1

            if row_counter > start_row:
                try:
                    row = json.loads(row)
                    parent_id = row['parent_id'].split('_')[1]
                    body = format_data(row['body'])
                    created_utc = row['created_utc']
                    score = row['score']
                    
                    comment_id = row['id']
                    
                    subreddit = row['subreddit']
                    parent_data = find_parent(parent_id)
                    
                    existing_comment_score = find_existing_score(parent_id)
                    if existing_comment_score:
                        if score > existing_comment_score:
                            if acceptable(body):
                                sql_insert_replace_comment(comment_id,parent_id,parent_data,body.encode('utf-8') ,subreddit,created_utc,score)
                                
                    else:
                        if acceptable(body):
                            if parent_data:
                                if score >= 2:
                                    sql_insert_has_parent(comment_id,parent_id,parent_data.encode('utf-8'),body.encode('utf-8') ,subreddit,created_utc,score)
                                    paired_rows += 1
                            else:
                                sql_insert_no_parent(comment_id,parent_id,body.encode('utf-8'),subreddit,created_utc,score)
                except Exception as e:
                    print(str(e))
                            
            if row_counter % 100000 == 0:
                print('Total Rows Read: {}, Paired Rows: {}, Time: {}'.format(row_counter, paired_rows, str(datetime.now())))

            if row_counter > start_row:
                if row_counter % cleanup == 0:
                    print("Cleanin up!")
                    sql = "DELETE FROM parent_reply WHERE parent IS NULL"
                    c.execute(sql)
                    connection.commit()
                    c.execute("VACUUM")
                    connection.commit()
                