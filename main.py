from flask import Flask, request, Response
import os
import uuid
import requests
from clawops import ClawOps

app = Flask(__name__)

client = ClawOps(
    api_key=os.environ.get("CLAWOPS_API_KEY", ""),
    account_id=os.environ.get("CLAWOPS_ACCOUNT_ID", ""),
)

CLAWOPS_FROM = "07052753884"
BASE_URL = os.environ.get("RAILWAY_URL", "http://localhost:8000")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
VOICE_ID = "onwK4e9ZLuTAKqWW03F9"

scripts = {}
audio_cache = {}

def split_sentences(text):
    import re
    sentences = re.split(r'(?<=[.!?。]) +', text.strip())
    return [s for s in sentences if s]

def generate_tts(text, audio_id):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    body = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.5, "similarity_boost": 0.75}
    }
    response = requests.post(url, headers=headers, json=body)
    if response.status_code == 200:
        audio_cache[audio_id] = response.content
        return True
    print(f"ElevenLabs 실패: {response.status_code} {response.text}")
    return False

@app.route("/call", methods=["POST"])
def make_call():
    data = request.json
    to = data.get("to", "").replace("-", "").replace("+82", "0")
    script = data.get("script", "안녕하세요. 코코입니다.")

    call_id = str(uuid.uuid4())[:8]
    sentences = split_sentences(script)

    audio_ids = []
    tts_success = True
    for i, sentence in enumerate(sentences):
        audio_id = f"{call_id}_{i}"
        if generate_tts(sentence, audio_id):
            audio_ids.append(audio_id)
        else:
            tts_success = False

    if tts_success and audio_ids:
        scripts[call_id] = {"mode": "elevenlabs", "audio_ids": audio_ids}
    else:
        scripts[call_id] = {"mode": "say", "sentences": sentences}

    call = client.calls.create(
        to=to,
        from_=CLAWOPS_FROM,
        url=f"{BASE_URL}/twiml?id={call_id}",
        timeout=120,
    )
    return {"call_id": call.call_id, "status": "initiated", "tts": "elevenlabs" if tts_success else "say"}

@app.route("/twiml", methods=["GET", "POST"])
def twiml():
    call_id = request.args.get("id", "")
    data = scripts.get(call_id, {})

    if data.get("mode") == "elevenlabs":
        tags = ""
        for audio_id in data["audio_ids"]:
            tags += f'<Play>{BASE_URL}/audio?id={audio_id}</Play>\n'
    elif data.get("mode") == "say":
        tags = ""
        for sentence in data["sentences"]:
            tags += f'<Say language="ko-KR">{sentence}</Say>\n'
    else:
        tags = '<Say language="ko-KR">안녕하세요. 코코입니다.</Say>\n'

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{tags}<Hangup/>
</Response>"""
    return Response(xml, mimetype="text/xml")

@app.route("/audio", methods=["GET"])
def audio():
    audio_id = request.args.get("id", "")
    if audio_id in audio_cache:
        audio_data = audio_cache[audio_id]
        return Response(
            audio_data,
            mimetype="audio/mpeg",
            headers={"Content-Length": len(audio_data)}
        )
    return "Not found", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)