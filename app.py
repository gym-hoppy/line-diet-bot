from flask import Flask, request, abort
import os
from dotenv import load_dotenv

# LINE SDK（v3でないが現行動作中）
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# OpenAIクライアント
from openai import OpenAI

# .env読み込み
load_dotenv()

# 各種キーを環境変数から取得
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Flaskアプリ作成
app = Flask(__name__)

# LINE Bot API設定
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# OpenAIクライアント初期化
client = OpenAI(api_key=OPENAI_API_KEY)

# system_message.txt を読み込む関数
def load_system_prompt():
    with open("system_message.txt", "r", encoding="utf-8") as f:
        return f.read()

# LINEからのメッセージ受け取り用エンドポイント
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# ユーザーからのテキストメッセージを処理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    system_prompt = load_system_prompt()

    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            { "role": "system", "content": system_prompt },
            { "role": "user", "content": user_message }
        ]
    )

    gpt_reply = response.choices[0].message.content

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=gpt_reply)
    )

# Renderで使うための起動設定
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)