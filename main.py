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
    return False

@app.route("/call", methods=["POST"])
def make_call():
    data = request.json
    to = data.get("to", "").replace("-", "").replace("+82", "0")
    script = data.get("script", "안녕하세요. 코코입니다.")

    call_id = str(uuid.uuid4())[:8]
    sentences = split_sentences(script)
    
    audio_ids = []
    for i, sentence in enumerate(sentences):
        audio_id = f"{call_id}_{i}"
        generate_tts(sentence, audio_id)
        audio_ids.append(audio_id)
    
    scripts[call_id] = audio_ids

    call = client.calls.create(
        to=to,
        from_=CLAWOPS_FROM,
        url=f"{BASE_URL}/twiml?id={call_id}",
    )
    return {"call_id": call.call_id, "status": "initiated"}

@app.route("/twiml", methods=["GET", "POST"])
def twiml():
    call_id = request.args.get("id", "")
    audio_ids = scripts.get(call_id, [])
    
    play_tags = ""
    for audio_id in audio_ids:
        if audio_id in audio_cache:
            play_tags += f'<Play>{BASE_URL}/audio?id={audio_id}</Play>\n'
    
    if not play_tags:
        play_tags = '<Say language="ko-KR">안녕하세요. 코코입니다.</Say>'

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{play_tags}
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