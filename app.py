import os
from dotenv import load_dotenv
load_dotenv()  # .env ファイルの読み込み

# FlaskというWebアプリの仕組みを使うために読み込みます
from flask import Flask, request, abort

# LINE Botを動かすための部品（SDK）を読み込みます
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage

# ChatGPTを使うためのOpenAIライブラリを読み込みます
import openai

# .env にあるキーを取得して使う
# OpenAIのAPIキーを設定
openai.api_key = os.getenv("OPENAI_API_KEY")

# LINE Developersから取得した情報をここに貼り付けます
LINE_CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
LINE_CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")

# FlaskというWebアプリの土台を作ります（サーバーを動かすための準備）
app = Flask(__name__)

# LINEとのやりとりをするための部品を用意します
line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

# LINEからのメッセージを受け取る「入口」の設定です
@app.route("/callback", methods=['POST'])
def callback():
    # LINEから送られてくる「署名（しょめい）」という安全確認の印を受け取ります
    signature = request.headers['X-Line-Signature']

    # メッセージの中身（テキストなど）を取得します
    body = request.get_data(as_text=True)

    # 安全確認（署名チェック）をして、問題がなければ処理を続けます
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        # 署名が間違っていたら「エラー」と返して止めます
        abort(400)

    # 正常に終わったら「OK」と返します
    return 'OK'

# LINEで「テキストメッセージ」が送られてきたときに反応する処理です（GPTに接続）
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_message = event.message.text

    # ChatGPTに問い合わせ
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",  # モデルは3.5でOK（高速・安価）
        messages=[
            {"role": "system", "content": "あなたは優しく親身なダイエットアドバイザーです。"},
            {"role": "user", "content": user_message}
        ]
    )

    gpt_reply = response['choices'][0]['message']['content']

    # ChatGPTの返答をLINEに返信
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=gpt_reply)
    )

# Render用：ポート番号を環境変数から取得し、Flaskを起動
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
