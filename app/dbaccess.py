import sqlite3
import json

#------DB保存------
# データベース接続とテーブル作成
def init_db():
    print("initialize database....")
    conn = sqlite3.connect('chatbot.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            message TEXT NOT NULL,
            response TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            profile_data TEXT
        )
    ''')
    conn.commit()
    conn.close()  

# メッセージをデータベースに保存
def save_message(user_id, message, response):
    conn = sqlite3.connect('chatbot.db')
    c = conn.cursor()
    c.execute('INSERT INTO messages (user_id, message, response) VALUES (?, ?, ?)', 
              (user_id, message, response))
    conn.commit()
    conn.close()

def save_profile(profile,user_id=None):
    conn = sqlite3.connect('chatbot.db')
    c = conn.cursor()
    c.execute('INSERT INTO user_profiles (user_id, profile_data) VALUES (?, ?)', 
            (user_id, profile))
    conn.commit()
    conn.close()

def get_last_conversations(user_id, limit=5):
    conn = sqlite3.connect('chatbot.db')
    c = conn.cursor()
    c.execute('SELECT message, response FROM messages WHERE user_id = ? ORDER BY id DESC LIMIT ?', (user_id, limit))
    conversations = c.fetchall()
    conn.close()
    return conversations

def get_profile(user_id, limit=3):
    conn = sqlite3.connect('chatbot.db')
    c = conn.cursor()
    c.execute('SELECT profile_data FROM user_profiles WHERE user_id = ? ORDER BY id DESC LIMIT ?', (user_id, limit))
    profiles = c.fetchall()
    conn.close()

    # 各JSON文字列をPythonの辞書に変換（タプルから文字列を取り出す）
    dict_list = [json.loads(item[0]) for item in profiles]  # タプルの最初の要素を取り出す

    # 一つの辞書に統合
    combined_dict = {}
    for d in dict_list:
        combined_dict.update(d)

    merged_profile = json.dumps(combined_dict, ensure_ascii=False, indent=2)
    #print("merged_profile:",merged_profile)

    return merged_profile

def db_access(sql,db_name,default_limit=5):
    print("sql:",sql)
    print("db_name:",db_name)
    # SQLクエリに LIMIT 句が含まれているか確認し、なければ追加
    sql = sql.strip().rstrip(';')
    if "LIMIT" not in sql.upper():
        sql += f" LIMIT {default_limit}"

    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute(sql)
    result = c.fetchall()
    print("result:",result)
    conn.close()

    return json.dumps(result, ensure_ascii=False, indent=2)

