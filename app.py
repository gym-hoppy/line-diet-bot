from flask import Flask, request, abort
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# LINE SDK（v3ではないが現行動作中）
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# OpenAI（v1.0以降の書き方）
from openai import OpenAI

# .envを読み込む
load_dotenv()

# 各種キーを.envから取得
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Flaskアプリの起動時刻を記録（スリープ復帰判定に使用）
boot_time = datetime.now()

# OpenAIクライアント初期化
client = OpenAI(api_key=OPENAI_API_KEY)

# Flaskアプリ作成
app = Flask(__name__)

# LINE Bot API設定
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# LINEからのメッセージを受け取るエンドポイント
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# LINEでテキストメッセージを受け取った時の処理
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text
    current_time = datetime.now()

    # 起動後5秒以内なら、ChatGPTには投げず、再送をお願いするメッセージだけ返す
    if (current_time - boot_time) < timedelta(seconds=5):
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="🤖 再起動完了！すみません、もう一度だけ同じメッセージを送ってもらえますか？🙏")
        )
        return

    # ChatGPTへメッセージを送信して応答を取得
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "あなたは親切で丁寧なダイエットアドバイザーです。"},
            {"role": "user", "content": user_message}
        ]
    )

    gpt_reply = response.choices[0].message.content

    # 応答をLINEに返信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=gpt_reply)
    )

# Render用：0.0.0.0＋PORT指定で起動
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)