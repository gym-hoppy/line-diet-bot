
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

# ローカル履歴保存ディレクトリ
HISTORY_DIR = "histories"
os.makedirs(HISTORY_DIR, exist_ok=True)

# 有料ユーザーIDリスト（現時点では空）
premium_user_ids = []

# ユーザー判定
def is_premium(user_id):
    return user_id in premium_user_ids

# systemメッセージ読み込み
def load_system_prompt():
    with open("system_message.txt", "r", encoding="utf-8") as f:
        return f.read()

# ユーザー履歴ファイルのパス
def get_history_path(user_id):
    return os.path.join(HISTORY_DIR, f"{user_id}.json")

# 履歴ロード（最大数制限付き）
def load_user_history(user_id, limit=4):
    path = get_history_path(user_id)
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            history = json.load(f)
        return history[-limit:]
    return []

# 履歴保存
def save_user_history(user_id, history):
    with open(get_history_path(user_id), "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

# 発言の重要性判定
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

    # 履歴読み込み（無料は最大4、有料は最大10件）
    history_limit = 10 if is_premium(user_id) else 4
    user_history = load_user_history(user_id, limit=history_limit)

    messages = [{"role": "system", "content": system_prompt}] + user_history
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.8
        )
        gpt_reply = response.choices[0].message.content.strip()
        if not gpt_reply:
            gpt_reply = "おっと、なんかワイの回路が止まってもうたかも…もう一回言うてくれるか？"
    except Exception as e:
        print("Error:", e)
        gpt_reply = "おっと、なんかワイの回路が止まってもうたかも…もう一回言うてくれるか？"

    # 履歴保存（有料でも無料でも重要発言だけ）
    if is_important_user_message(user_message):
        user_history.append({"role": "user", "content": user_message})
    if is_important_assistant_message(gpt_reply):
        user_history.append({"role": "assistant", "content": gpt_reply})
    save_user_history(user_id, user_history)

    # LINE返信
    line_bot_api.reply_message(event.reply_token, TextSendMessage(text=gpt_reply))

# ローカル or Render起動用
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)