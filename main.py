from flask import Flask, request, Response
import os
import urllib.parse
from clawops import ClawOps

app = Flask(__name__)

client = ClawOps(
    api_key=os.environ.get("CLAWOPS_API_KEY", ""),
    account_id=os.environ.get("CLAWOPS_ACCOUNT_ID", ""),
)

CLAWOPS_FROM = "07052753884"
BASE_URL = os.environ.get("RAILWAY_URL", "http://localhost:8000")

scripts = {}

@app.route("/call", methods=["POST"])
def make_call():
    data = request.json
    to = data.get("to", "").replace("-", "").replace("+82", "0")
    script = data.get("script", "안녕하세요. 코코입니다.")

    import uuid
    call_id = str(uuid.uuid4())[:8]
    scripts[call_id] = script

    call = client.calls.create(
        to=to,
        from_=CLAWOPS_FROM,
        url=f"{BASE_URL}/twiml?id={call_id}",
    )
    return {"call_id": call.call_id, "status": "initiated"}

@app.route("/twiml", methods=["GET", "POST"])
def twiml():
    call_id = request.args.get("id", "")
    script = scripts.get(call_id, "안녕하세요. 코코입니다.")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="ko-KR">{script}</Say>
</Response>"""
    return Response(xml, mimetype="text/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)