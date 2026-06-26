from flask import Flask, request, Response
import os
import uuid
import requests
from clawops import ClawOps

app = Flask(__name__)

clawops_client = ClawOps(
    api_key=os.environ.get("CLAWOPS_API_KEY", ""),
    account_id=os.environ.get("CLAWOPS_ACCOUNT_ID", ""),
)

CLAWOPS_FROM = "07052753884"
BASE_URL = os.environ.get("RAILWAY_URL", "https://api.wondanmarket.com")
ELEVENLABS_API_KEY = os.environ.get("ELEVENLABS_API_KEY", "")
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
VOICE_ID = "onwK4e9ZLuTAKqWW03F9"

call_scripts = {}

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

@app.route("/pipecat-session", methods=["POST"])
def pipecat_session():
    from pipecat.pipeline.pipeline import Pipeline
    from pipecat.pipeline.runner import PipelineRunner
    from pipecat.pipeline.task import PipelineTask
    from pipecat.services.elevenlabs.tts import ElevenLabsTTSService
    from pipecat.services.anthropic.llm import AnthropicLLMService
    from pipecat.services.openai.stt import OpenAISTTService
    from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
    from pipecat.transports.network.fastapi_websocket import FastAPIWebsocketTransport, FastAPIWebsocketParams
    from pipecat.audio.vad.silero import SileroVADAnalyzer

    data = request.json
    call_id = data.get("call_id", "")
    system_prompt = call_scripts.get(call_id, {}).get("system_prompt", "당신은 친절한 AI 전화 대리 서비스입니다.")

    return {"status": "ok", "call_id": call_id}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)