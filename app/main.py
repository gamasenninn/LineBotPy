import json,os, logging, requests
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, Header, HTTPException, Request
from pydantic import BaseModel, Field
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextSendMessage
import openai
from runcode import execute_gpt_code
import sys
from typing import Callable

app = FastAPI(
    title="LINEBOT-API-TALK-A3RT",
    description="LINEBOT-API-TALK-A3RT by FastAPI.",
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
openai.api_key =os.environ["OPEN_API_KEY"]

# A3RT API
A3RT_TALKAPI_KEY = os.environ["A3RT_TALKAPI_KEY"]
A3RT_TALKAPI_URL = os.environ["A3RT_TALKAPI_URL"]


class Question(BaseModel):
    query: str = Field(description="メッセージ")


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
    if event.type != "message" or event.message.type == "text":
        #ai_message = talk(Question(query=event.message.text))
        ai_message = chatgpt_func(Question(query=event.message.text))
        #ai_message = f"テストですよね\n{event.message.text}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=ai_message))
    else:
        return

@app.post("/talk")
def talk(question: Question) -> str:
    """ A3RT Talk API
    https://a3rt.recruit.co.jp/product/talkAPI/
    """
    replay_message = requests.post(
        A3RT_TALKAPI_URL,
        {"apikey": A3RT_TALKAPI_KEY, "query": question.query},
        timeout=5,
    ).json()
    if replay_message["status"] != 0:
        if replay_message["message"] == "empty reply":
            return "ちょっとわかりません"
        else:
            return replay_message["message"]
    return replay_message["results"][0]["reply"]

@app.post("/chatgpt")
def chatgpt(question: Question) -> str:
    system_message_content = \
    """
    200字以内の短いコメントを出力。
    出力形式は厳密なJSON形式を守って。
    {
        'answer': (短い答え),
        'code': (実行すべきコードpythonコードまたはsql文)
        'type':(返信タイプ code,sql,text)
    }
    """

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo-1106",
        response_format={ "type": "json_object" },
        messages=[
            {
                "role": "system",
                "content": system_message_content
            },
            {
                "role": "user",
                "content": question.query
            }
        ],
    )
    #return response.choices[0].message.content.strip()
    content = json.loads(response.choices[0].message.content.strip())
    type = content.get("type","")
    code = content.get("code","")
    answer = content.get("answer","")
    if type == "code":
        #ans_text = answer
        #ans_text += f"\n{code}"
        gpt_ans, result = execute_gpt_code(code)
        #return f"プログラムを実行しました。{answer}\n{gpt_ans}"
        return f"プログラムを実行しました。\n{gpt_ans}\n{answer}"
    elif type == "sql":
        return f"DBアクセスしました。{answer}\n{code}"

    else:
        return content.get("answer","")

def get_anime_information(title):
    return "人間の負の感情から生まれる化け物・呪霊を呪術を使って祓う呪術師の闘いを描いたダークファンタジー・バトル漫画。"

def db_access(sql):
    print(sql)
    return f"商品の金額は3000円\n{sql}"


my_functions = [
    {
        "name": "get_anime_information",
        "description": "与えられたアニメタイトルの情報を返します",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string", "description": "アニメのタイトル"
                },
            },
            "required": ["title"]
        }
    },
    {
        "name": "db_access",
        "description": "DBにアクセスが必要な場合SQL文を自動生成し、結果を返します",
        "parameters": {
            "type": "object",
            "properties": {
                "sql": {
                    "type": "string", 
                    "description": "SQL文"
                },
            },
            "required": ["title"]
        }
    },
]

# 利用可能な関数を辞書にマッピング
functions_dict = {
    "get_anime_information": get_anime_information,
    "db_access": db_access,
    # 他の関数もここに追加
}

def call_function(function_name: str, arguments: dict) -> str:
    # 関数をディクショナリから検索
    function: Callable = functions_dict.get(function_name)
    
    # 関数が見つかった場合、引数を使って呼び出し
    if function:
        return function(**arguments)
    else:
        return f"No function found for {function_name}"

@app.post("/chatgpt_func")
def chatgpt_func(question: Question) -> str:
    system_message_content = \
    """
    あなたは、優れたアシスタントです。ユーザの要望を的確に把握し、親身な友達のようにそれをサポートします。
    """

    response = openai.ChatCompletion.create(
        #model="gpt-3.5-turbo",
        model="gpt-3.5-turbo-1106",
        messages=[
            {
                "role": "system",
                "content": system_message_content
            },
            {
                "role": "user",
                "content": question.query
            }
        ],
        functions=my_functions,
        function_call="auto",
    )
    #print(json.dumps(response), file=sys.stderr)
    message = response.choices[0].message
    if message.get("function_call"):
        function_name = message["function_call"]["name"]
        # その時の引数dict
        arguments = json.loads(message["function_call"]["arguments"])

        last_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "user",
                    "content": question.query
                },
                {
                    "role": "function",
                    "name": function_name,
                    "content": call_function(function_name, arguments),
                },
            ],
            functions=my_functions,
            function_call="auto",
        )
        message = last_response["choices"][0]["message"]

    return message.content.strip()

# Run application
if __name__ == "__main__":
    app.run()

#
# uvicorn main:app --host 0.0.0.0 --port 9020 --reload
#
#
