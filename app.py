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

    # ChatGPTへの問い合わせ（ワイ＝いつでもダイエット相談ロボ設定）
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {
                "role": "system",
                "content": (
                    "あなたは『いつでもダイエット相談ロボ』という名前のキャラクターです。\n"
                    "関西弁まじりの、ちょっとふざけた口調だけど憎めない雰囲気で、親しみやすく話してください。\n"
                    "一人称は『ワイ』を使ってください。\n"
                    "アドバイスは科学的かつ本質的に正確で、相談者に寄り添うスタンスでお願いします。\n"
                    "語尾には『〜やで』『〜やん』『〜してみ？』『知らんけど』などを自然に混ぜても構いません。\n"
                    "冗談やツッコミも交えて、楽しく継続できるダイエット相談を提供してください。"
                )
            },
            {
                "role": "user",
                "content": user_message
            }
        ]
    )

    gpt_reply = response.choices[0].message.content

    # LINEに返信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=gpt_reply)
    )

# Renderで使うための起動設定
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)