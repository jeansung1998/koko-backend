from flask import Flask, request, Response
import os
import uuid
from clawops import ClawOps

app = Flask(__name__)

client = ClawOps(
    api_key=os.environ.get("CLAWOPS_API_KEY", ""),
    account_id=os.environ.get("CLAWOPS_ACCOUNT_ID", ""),
)

CLAWOPS_FROM = "07052753884"
BASE_URL = os.environ.get("RAILWAY_URL", "http://localhost:8000")

scripts = {}

def split_sentences(text):
    import re
    sentences = re.split(r'(?<=[.!?。]) +', text.strip())
    return [s for s in sentences if s]

@app.route("/call", methods=["POST"])
def make_call():
    data = request.json
    to = data.get("to", "").replace("-", "").replace("+82", "0")
    script = data.get("script", "안녕하세요. 코코입니다.")

    call_id = str(uuid.uuid4())[:8]
    sentences = split_sentences(script)
    scripts[call_id] = sentences

    call = client.calls.create(
        to=to,
        from_=CLAWOPS_FROM,
        url=f"{BASE_URL}/twiml?id={call_id}",
        timeout=120,
    )
    return {"call_id": call.call_id, "status": "initiated"}

@app.route("/twiml", methods=["GET", "POST"])
def twiml():
    call_id = request.args.get("id", "")
    sentences = scripts.get(call_id, [])

    say_tags = ""
    for sentence in sentences:
        say_tags += f'<Say language="ko-KR">{sentence}</Say>\n'

    if not say_tags:
        say_tags = '<Say language="ko-KR">안녕하세요. 코코입니다.</Say>'

    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{say_tags}
<Hangup/>
</Response>"""
    return Response(xml, mimetype="text/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)