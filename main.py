# ============================================================
# KOKO AI 전화대리 서비스 백엔드
# ============================================================
from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

CLAWOPS_API_KEY = os.environ.get("CLAWOPS_API_KEY", "")
CLAWOPS_ACCOUNT_ID = os.environ.get("CLAWOPS_ACCOUNT_ID", "")
CLAWOPS_FROM = "07052753884"

@app.route("/call", methods=["POST"])
def make_call():
    data = request.json
    to = data.get("to", "").replace("-", "").replace("+82", "0")
    system_prompt = data.get("system_prompt", "당신은 친절한 AI 전화 대리 서비스 코코입니다. 짧고 자연스럽게 대화하세요.")

    # ClawOps REST API 직접 호출 (CamelCase 필수)
    response = requests.post(
        f"https://api.claw-ops.com/v1/accounts/{CLAWOPS_ACCOUNT_ID}/calls",
        headers={
            "Authorization": f"Bearer {CLAWOPS_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "To": to,
            "From": CLAWOPS_FROM,
            "AI": {
                "Provider": "openai",
                "Model": "gpt-realtime",
                "ApiKey": os.environ.get("OPENAI_API_KEY", ""),
                "Voice": "marin",
                "Language": "ko",
                "Greeting": True,
                "Messages": [
                    {"role": "system", "content": system_prompt}
                ]
            }
        }
    )

    result = response.json()
    return jsonify({"call_id": result.get("callId", ""), "status": "initiated"})

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)