
import os
import json
from flask import Flask, request, abort
from dotenv import load_dotenv
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from openai import OpenAI

# 初期化
load_dotenv()
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ユーザーごとの発言履歴保存用（簡易ファイルDB）
HISTORY_DIR = "histories"
os.makedirs(HISTORY_DIR, exist_ok=True)

def load_system_prompt():
    with open("system_message.txt", "r", encoding="utf-8") as f:
        return f.read()

def get_history_path(user_id):
    return os.path.join(HISTORY_DIR, f"{user_id}.json")

def load_user_history(user_id):
    path = get_history_path(user_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_user_history(user_id, history):
    with open(get_history_path(user_id), "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def is_important_user_message(text):
    return len(text.strip()) >= 10 and any(keyword in text.lower() for keyword in ["どう", "なに", "なぜ", "できる", "無理", "食べ", "痩せ", "運動", "カロリー"])

def is_important_assistant_message(text):
    return any(keyword in text for keyword in ["〜したらええ", "おすすめ", "続けて", "やってみ", "気にせんでええ", "重要", "考え方", "工夫"])

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_id = event.source.user_id
    user_message = event.message.text.strip()
    system_prompt = load_system_prompt()

    # 履歴読み込み（最大4件）
    full_history = load_user_history(user_id)[-4:]
    messages = [{"role": "system", "content": system_prompt}] + full_history
    messages.append({"role": "user", "content": user_message})

    # ChatGPT呼び出し
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.8
    )
    reply = response.choices[0].message.content

    # 条件を満たす発言のみ履歴保存
    history = load_user_history(user_id)
    if is_important_user_message(user_message):
        history.append({"role": "user", "content": user_message})
    if is_important_assistant_message(reply):
        history.append({"role": "assistant", "content": reply})
    save_user_history(user_id, history)

    # LINE返信
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

# ローカル or Render起動用
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
