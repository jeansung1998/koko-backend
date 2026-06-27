# ============================================================
# KOKO AI 전화대리 서비스 백엔드
# ============================================================
# [성공 확인된 것들]
# - ClawOps 070번호로 발신 성공
# - api.wondanmarket.com 커스텀 도메인 연결됨
# - GitHub 자동배포 연결됨
# ============================================================

from flask import Flask, request
import os
from clawops import ClawOps

app = Flask(__name__)

clawops_client = ClawOps(
    api_key=os.environ.get("CLAWOPS_API_KEY", ""),
    account_id=os.environ.get("CLAWOPS_ACCOUNT_ID", ""),
)

CLAWOPS_FROM = "07052753884"

@app.route("/call", methods=["POST"])
def make_call():
    data = request.json
    to = data.get("to", "").replace("-", "").replace("+82", "0")
    system_prompt = data.get("system_prompt", "당신은 친절한 AI 전화 대리 서비스 코코입니다. 짧고 자연스럽게 대화하세요.")

    call = clawops_client.calls.create(
        to=to,
        from_=CLAWOPS_FROM,
        ai={
            "provider": "openai",
            "model": "gpt-realtime",
            "api_key": os.environ.get("OPENAI_API_KEY", ""),
            "voice": "marin",
            "language": "ko",
            "messages": [{"role": "system", "content": system_prompt}],
            "greeting": True,
            "turn_detection": {
                "type": "semantic_vad",
                "eagerness": "medium"
            }
        }
    )
    return {"call_id": call.call_id, "status": "initiated"}

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)