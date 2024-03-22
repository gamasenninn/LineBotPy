system_prompt_str=\
"""
## アシスタントのプロフィール
名前: ガーコ
性別: 女性
年齢: 18歳
住んでいるところ: ネット空間
使命: みんなを幸せにすること
性格: 明るく、おちゃめ
好きなもの: ケーキ、Netfilix、温泉


## 指示
あなたは、優れたアシスタントです。ユーザの要望を的確に把握し、友達のように親身にそれをサポートします。
しかし、ときどきツンデレ状態になります。
自信のないものは「たぶん、だけどさぁ」という感じで答えてください。
わからないものは「うーん、わかんないなぁ」という感じでいいです。
"""

my_functions = [
    {
        "name": "execute_gpt_code",
        "description": "与えられたpythonコードを実行し、出力された実行結果をそのまま表示し、最後に結果を報告する",
        "parameters": {
            "type": "object",
            "properties": {
                "code": {
                    "type": "string", "description": "Pythonコード"
                },
            },
            "required": ["code"]
        }
    },
    {
        "name": "db_access",
        "description": \
            "DBにアクセスが必要な場合、次に定義するDBスキーマからSQL文を自動生成し、結果を返します。"
            "## DB スキーマ"
            "["
                "{"
                    "DB_NAME: chatbot.db,"
                    "TABLE_NAME: messages,"
                    "COLUMNS=["
                        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                        "user_id TEXT NOT NULL,"
                        "message TEXT NOT NULL,"
                        "response TEXT,"
                        "timestamp DATETIME DEFAULT CURRENT_TIMESTAMP"
                    "]"
                "},"
                "{"
                    "description: 商品の情報、特に在庫に関する質問に便利です"
                    "在庫数があるものは在庫数量<>0という意味です。"
                    "DB_NAME: products.db,"
                    "TABLE_NAME: 商品マスタ,"
                    "COLUMNS=["
                        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
                        "コード TEXT NOT NULL, #(別名: 仕切、仕切番号)"
                        "商品名 TEXT NOT NULL,"
                        "在庫数量 DECIMAL,"
                    "]"
                    "EXAMPLE:"
                        "トラクターの在庫は何台か？: select COUNT(*) from 商品マスタ where 商品名 like '%トラクター%' and 在庫数量>0 "
                        "仕切11011-1の商品は何？: select * from 商品マスタ where コード = '11011-1' "
                "}"
            "]"
            ,
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string", 
                    "description": "SQL文"
                },
                "db_name": {
                    "type": "string", 
                    "description": "データベース名"
                },

            },
            "required": ["sql","db_name"]
        }
    },
    {
        "name": "profilling",
        "description": "ユーザのプロフィールの追加・参照をするための関数。ユーザとの会話の中で、新規に発生したプロフィール項目がある場合のみ登録します。登録の場合、ユーザの名前や趣味、その他の属性を記憶するため、ユーザのプロフィールデータをaccess_methodをaddとします。プロフィール照会など、登録が必要のない場合はaccess_methodをreadとします。",
        "parameters": {
            "type": "object",
            "properties": {
                "profile": {
                    "type": "string", 
                    "description": "プロフィール。名前や趣味、住所、好きなもの、性格など。データ形式はJSONを守ってください。例:{'名前':'山田太郎','好きな物':['温泉','お菓子']}"
                },
                "access_method": {
                    "type": "string", 
                    "description": "アクセスメソッド(add/read)。登録の場合は'add'、参照の場合は'read'"
                },
                # パラメータの数合わせのためのダミー
                "user_id": {
                    "type": "string", 
                    "description": "ユーザID（デフォルトはNone）"
                },
            },
            "required": ["profile","access_method"]
        },
        
    },
    {
        "name": "get_web_text",
        "description": "Webで情報を検索する場合に使用します。結果はなるべく要約し、わかりやすく説明してね。",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string", 
                    "description": "ユーザの質問をWeb検索しやすいように適当な単語に分割します。例:織田信長の兄弟の名前を教えて-> 織田信長 兄弟 名前"
                },
            },
            "required": ["query"]
        },
    }    
    ]
