# ============================================================
# KOKO AI 전화대리 서비스 백엔드
# ============================================================
# [작업 공정]
# STEP 1. 전화 발신 (/call) ✅ 완성
# STEP 2. TwiML 응답 (/twiml) ✅ 완성 - 인트로 멘트 + WebSocket 스트림 연결
# STEP 3. 실시간 WebSocket 스트림 (/stream) ⚠️ 미완성 - 연결은 되나 STT→Claude→TTS 루프 미작동
# ============================================================
# [성공 확인된 것들]
# - ClawOps 070번호로 발신 성공
# - Say language="ko-KR" TTS 작동
# - Hangup 정상
# - ElevenLabs TTS ulaw_8000 포맷 생성 성공
# - GitHub 자동배포 연결됨
# - api.wondanmarket.com 커스텀 도메인 연결됨 (WebSocket 30초 제한 해제)
# ============================================================
# [현재 막힌 것]
# - /stream WebSocket 연결 시 HTTP Status 0 또는 404 반환
# - gunicorn worker 설정 문제로 추정 (sync/gthread/geventwebsocket 모두 시도했으나 실패)
# ============================================================

from flask import Flask, request, Response
from flask_sock import Sock
import os
import uuid
import requests
import json
import base64
import anthropic
from openai import OpenAI
from clawops import ClawOps

app = Flask(__name__)
sock = Sock(app)

# ============================================================
# 클라이언트 초기화
# - ClawOps: 전화 발신 담당 (계정 ID, API 키 Railway 환경변수에 저장)
# - OpenAI: Whisper STT 담당
# - Anthropic: Claude 대화 담당
# ============================================================
clawops_client = ClawOps(
    api_key=os.environ.get("CLAWOPS_API_KEY", ""),
    account_id=os.environ.get("CLAWOPS_ACCOUNT_ID", ""),
)
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
anthropic_client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY", ""))

# ============================================================
# 환경변수
# - CLAWOPS_FROM: 발신 070 번호
# - RAILWAY_URL: 커스텀 도메인 (WebSocket 30초 제한 해제용)
# - ELEVENLABS_API_KEY: TTS API 키
# - VOICE_ID: ElevenLabs 음성 ID
# ============================================================
CLAWOPS_FROM = "07052753884"
BASE_URL = os.environ.get("RAILWAY_URL", "https://api.wondanmarket.com")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
VOICE_ID = "onwK4e9ZLuTAKqWW03F9"

call_scripts = {}

# ============================================================
# STEP 3-1. TTS 생성 함수 ✅ 성공 확인
# - ElevenLabs API로 텍스트 → 음성 변환
# - ulaw_8000 포맷: ClawOps 전화 스트림 호환 포맷
# ============================================================
def generate_tts_bytes(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        "output_format": "ulaw_8000"
    }
    response = requests.post(url, headers=headers, json=body)
    if response.status_code == 200:
        return response.content
    return None

# ============================================================
# STEP 3-2. STT 함수 ⚠️ 미검증
# - OpenAI Whisper로 음성 → 텍스트 변환
# - 한국어(ko) 지정
# - WebSocket 연결 실패로 아직 실제 테스트 못함
# ============================================================
def stt(audio_bytes):
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        f.write(audio_bytes)
        f.flush()
        with open(f.name, "rb") as audio_file:
            transcript = openai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ko"
            )
    return transcript.text

# ============================================================
# STEP 3-3. Claude 응답 함수 ⚠️ 미검증
# - Claude Haiku로 빠른 응답 생성
# - system_prompt로 코코 역할 정의
# - WebSocket 연결 실패로 아직 실제 테스트 못함
# ============================================================
def ask_claude(user_text, system_prompt):
    message = anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=200,
        system=system_prompt,
        messages=[{"role": "user", "content": user_text}]
    )
    return message.content[0].text

# ============================================================
# STEP 1. 전화 발신 API ✅ 완성
# - Flutter 앱에서 POST /call 호출
# - to: 수신자 번호, script: 인트로 멘트, system_prompt: AI 역할 정의
# - ClawOps로 발신 후 /twiml URL 전달
# ============================================================
@app.route("/call", methods=["POST"])
def make_call():
    data = request.json
    to = data.get("to", "").replace("-", "").replace("+82", "0")
    script = data.get("script", "안녕하세요. 코코입니다.")
    system_prompt = data.get("system_prompt", "당신은 친절한 AI 전화 대리 서비스입니다. 짧고 자연스럽게 대화하세요.")

    call_id = str(uuid.uuid4())[:8]
    call_scripts[call_id] = {
        "intro": script,
        "system_prompt": system_prompt
    }

    call = clawops_client.calls.create(
        to=to,
        from_=CLAWOPS_FROM,
        url=f"{BASE_URL}/twiml?id={call_id}",
        timeout=120,
    )
    return {"call_id": call.call_id, "status": "initiated"}

# ============================================================
# STEP 2. TwiML 응답 ✅ 완성
# - ClawOps가 전화 연결 후 이 URL 호출
# - Say: 인트로 멘트 재생 (ko-KR 필수, ko는 오류 발생)
# - Connect/Stream: WebSocket으로 실시간 오디오 스트림 연결
# - wss:// 프로토콜 사용 (https → wss 자동 변환)
# ============================================================
@app.route("/twiml", methods=["GET", "POST"])
def twiml():
    call_id = request.args.get("id", "")
    data = call_scripts.get(call_id, {})
    intro = data.get("intro", "안녕하세요. 코코입니다.")
    ws_url = BASE_URL.replace('https://', 'wss://').replace('http://', 'ws://')

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
  <Say language="ko-KR">{intro}</Say>
  <Connect>
    <Stream url="{ws_url}/stream?id={call_id}"/>
  </Connect>
</Response>"""
    return Response(xml, mimetype="text/xml")

# ============================================================
# STEP 3. 실시간 WebSocket 스트림 ⚠️ 미완성
# - ClawOps가 /stream으로 WebSocket 연결 시도
# - 현재 문제: HTTP Status 0 반환 (연결 실패)
# - 시도한 것: geventwebsocket worker, gthread worker 모두 실패
# - 다음 시도: uvicorn + websockets 라이브러리로 교체 예정
# ============================================================
@sock.route("/stream")
def stream(ws):
    call_id = request.args.get("id", "")
    data = call_scripts.get(call_id, {})
    system_prompt = data.get("system_prompt", "당신은 친절한 AI 전화 대리 서비스입니다. 짧고 자연스럽게 대화하세요.")

    audio_buffer = bytearray()
    stream_sid = None
    silence_count = 0
    SILENCE_THRESHOLD = 20  # 1초 침묵 감지 (timeout=1초 * 20회)

    while True:
        try:
            msg = ws.receive(timeout=1)
        except Exception:
            break

        if msg is None:
            silence_count += 1
            if silence_count >= SILENCE_THRESHOLD and len(audio_buffer) > 0:
                # 침묵 감지 → STT → Claude → TTS → 재생
                try:
                    text = stt(bytes(audio_buffer))
                    if text.strip():
                        response_text = ask_claude(text, system_prompt)
                        tts_audio = generate_tts_bytes(response_text)
                        if tts_audio and stream_sid:
                            payload = base64.b64encode(tts_audio).decode("utf-8")
                            ws.send(json.dumps({
                                "event": "media",
                                "streamSid": stream_sid,
                                "media": {"payload": payload}
                            }))
                except Exception as e:
                    print(f"처리 오류: {e}")
                audio_buffer.clear()
                silence_count = 0
            continue

        silence_count = 0
        try:
            event = json.loads(msg)
        except Exception:
            continue

        if event.get("event") == "start":
            stream_sid = event.get("start", {}).get("streamId")

        elif event.get("event") == "media":
            payload = event.get("media", {}).get("payload", "")
            audio_buffer.extend(base64.b64decode(payload))

        elif event.get("event") == "stop":
            break

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)