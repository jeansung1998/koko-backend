# ============================================================
# KOKO AI 전화대리 서비스 백엔드
# ============================================================
# [작업 공정]
# STEP 1. 전화 발신 (/call) ✅ 완성
#   - ClawOps ai 파라미터로 OpenAI Realtime 직접 연결
#   - WebSocket 서버 불필요 (ClawOps가 내부 처리)
# ============================================================
# [성공 확인된 것들]
# - ClawOps 070번호로 발신 성공
# - api.wondanmarket.com 커스텀 도메인 연결됨
# - GitHub 자동배포 연결됨
# - Railway OPENAI_API_KEY 환경변수 설정됨
# ============================================================

from flask import Flask, request
import os
from clawops import ClawOps

app = Flask(__name__)

# ============================================================
# 클라이언트 초기화
# - ClawOps: 전화 발신 담당
# - API 키, 계정 ID는 Railway 환경변수에 저장
# ============================================================
clawops_client = ClawOps(
    api_key=os.environ.get("CLAWOPS_API_KEY", ""),
    account_id=os.environ.get("CLAWOPS_ACCOUNT_ID", ""),
)

CLAWOPS_FROM = "07052753884"

# ============================================================
# STEP 1. 전화 발신 API ✅
# - Flutter 앱에서 POST /call 호출
# - to: 수신자 번호
# - script: AI 시스템 프롬프트 (코코가 할 일)
# - ClawOps ai 파라미터로 OpenAI Realtime 직접 연결
# - WebSocket, TwiML, STT, TTS 코드 불필요
# ============================================================
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
        },
    )
    return {"call_id": call.call_id, "status": "initiated"}

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)