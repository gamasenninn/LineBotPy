import json,os, logging, requests
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, Header, HTTPException, Request
from pydantic import BaseModel, Field
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextSendMessage
from runcode import execute_gpt_code
import sys
from typing import Callable
from openai import OpenAI
from linebot.exceptions import LineBotApiError
from system_prompt import system_prompt_str,my_functions
from dbaccess import (
    init_db,
    save_message,
    get_last_conversations,
    save_profile,
    get_profile,
    db_access
)
from web_search import get_web_text


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
    group_id = event.source.group_id if hasattr(event.source, 'group_id') else ''

    print("type:",event.source.type)
    print("user:",user_id)
    print("group:",group_id)

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


# 利用可能な関数を辞書にマッピング
functions_dict = {
    "execute_gpt_code": execute_gpt_code,
    "db_access": db_access,
    "profilling": profilling,
    "get_web_text": get_web_text,

    # 他の関数もここに追加
}

def call_function(function_name: str, user_id: str,arguments: dict) -> str:

    print("function_name",function_name)

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


    # 初回の質問。自動振り分けをする。
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

        # TODO: 過去の会話履歴をぶち込むかどうか検討
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
