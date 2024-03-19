import json,os, logging, requests
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, Header, HTTPException, Request
from pydantic import BaseModel, Field
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextSendMessage
#import openai
from runcode import execute_gpt_code
import sys
from typing import Callable
from openai import OpenAI
from linebot.exceptions import LineBotApiError
from system_prompt import system_prompt_str
#import sqlite3
from dbaccess import (
    init_db,
    save_message,
    get_last_conversations,
    save_profile,
    get_profile,
    db_access
)
app = FastAPI(
    title="LINEBOT-API-CHATGPT",
    description="LINEBOT-API-CHATGPT by FastAPI.",
    version="1.0",
)

# ApiRoot Health Check
@app.get("/")
def api_root():
    return {"message": "LINEBOT-API is Healthy!"}


load_dotenv()

# LINE Messaging APIの準備
line_bot_api = LineBotApi(os.environ["CHANNEL_ACCESS_TOKEN"])
handler = WebhookHandler(os.environ["CHANNEL_SECRET"])

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.environ["OPEN_API_KEY"],
)

class Question(BaseModel):
    query: str = Field(description="メッセージ")
    userid: str = Field(description="ユーザID")

@app.post("/callback")
async def callback(
    request: Request,
    background_tasks: BackgroundTasks,
    x_line_signature=Header(None),
    summary="LINE Message APIからのコールバックです。"
):
    body = await request.body()
    try:
        background_tasks.add_task(
            handler.handle, body.decode("utf-8"), x_line_signature
        )
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return "ok"


# LINE Messaging APIからのメッセージイベントを処理
@handler.add(MessageEvent)
def handle_message(event):

    user_id = event.source.user_id
    user_message = event.message.text

    try:
        if event.type != "message" or event.message.type == "text":
            # ここにメッセージ処理のロジックを記述
            ai_message = chatgpt_func(Question(query=user_message,userid=user_id))
            if not ai_message:
                ai_message = "申し訳ありません、回答を生成できませんでした。"            
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ai_message))
            # メッセージをデータベースに保存
            save_message(user_id, user_message, ai_message)            
        else:
            return
    except LineBotApiError as e:
        # LINE APIエラーが発生した場合の処理
        error_message = f"LINE送信時、エラーが発生しました: {e.message}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=error_message))
        print("Line API ERROR:",e)
    except Exception as e:
        # その他のエラーが発生した場合の処理
        error_message = "予期せぬエラーが発生しました。"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=error_message))
        print(e)

def profilling(profile,access_method='read',user_id=None):
    #print("profile",profile)
    #print("user_id",user_id)
    print("access method",access_method)
    if access_method == 'add':
        save_profile(profile,user_id)
    else:
        profile = get_profile(user_id, limit=30)
    return profile

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
        }
    },]

# 利用可能な関数を辞書にマッピング
functions_dict = {
    "execute_gpt_code": execute_gpt_code,
    "db_access": db_access,
    "profilling": profilling,
    # 他の関数もここに追加
}

def call_function(function_name: str, user_id: str,arguments: dict) -> str:

    #print("function_name",function_name)

    # 関数をディクショナリから検索
    function: Callable = functions_dict.get(function_name)
    
    if function_name in ['profilling']:
        arguments['user_id'] = user_id

    #print("args:",arguments)

    # 関数が見つかった場合、引数を使って呼び出し
    if function:
        return function(**arguments)
    else:
        return f"No function found for {function_name}"

@app.post("/chatgpt_func")
def chatgpt_func(question: Question) -> str:
    user_id = question.userid
    profile = get_profile(user_id)
    system_message_content = system_prompt_str + \
    f"""
    ## ユーザのプロファイル
    {profile}
    """
    past_conversations = get_last_conversations(user_id)
    # 過去の会話をメッセージリストに追加
    messages = [
        {
            "role": "system",
            "content": system_message_content
        },
    ]
    for message, response in reversed(past_conversations):
        messages.append({"role": "user", "content": message})
        messages.append({"role": "assistant", "content": response})

    # 現在のユーザーの質問を追加
    messages.append({"role": "user", "content": question.query})

    print("messages:",messages)

    response = client.chat.completions.create(
        #model="gpt-3.5-turbo",
        model="gpt-3.5-turbo-1106",
        messages=messages,
        functions=my_functions,
        function_call="auto",
    )
    #print(json.dumps(response), file=sys.stderr)
    message = response.choices[0].message
    if message.function_call:
        function_name = message.function_call.name
        # その時の引数dict
        arguments = json.loads(message.function_call.arguments)

        last_response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": system_message_content
                },
                {
                    "role": "user",
                    "content": question.query
                },
                {
                    "role": "function",
                    "name": function_name,
                    "content": call_function(function_name, user_id,arguments),
                },
            ],
            functions=my_functions,
            function_call="auto",
        )
        message = last_response.choices[0].message
        print(message.content, file=sys.stderr)

    return message.content


# Run application
if __name__ == "__main__":
    init_db()
    app.run()

#
# uvicorn main:app --host 0.0.0.0 --port 9020 --reload
#
#
