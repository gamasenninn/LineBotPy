import json, os, logging, requests
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, Header, HTTPException, Request
from pydantic import BaseModel, Field
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextSendMessage
import openai

app = FastAPI(
    title="LINEBOT-API-TALK-A3RT",
    description="LINEBOT-API-TALK-A3RT by FastAPI.",
    version="1.0",
)

# ApiRoot Health Check
@app.get("/")
def api_root():
    return {"message": "LINEBOT-API-TALK-A3RT Healthy!"}


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
        ai_message = chatgpt(Question(query=event.message.text))
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
        'ansewer': (短い答え),
        'type':(返信タイプ)

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
    return response.choices[0].message.content.strip()
# Run application
if __name__ == "__main__":
    app.run()

