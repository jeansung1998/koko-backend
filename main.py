from flask import Flask, request, Response
import requests
import os

app = Flask(__name__)

CLAWOPS_API_KEY = os.environ.get("CLAWOPS_API_KEY", "")
CLAWOPS_ACCOUNT_ID = os.environ.get("CLAWOPS_ACCOUNT_ID", "ACac4j80utqXeSeK9w")
CLAWOPS_FROM = "07052753884"
BASE_URL = os.environ.get("RAILWAY_URL", "http://localhost:8000")

@app.route("/call", methods=["POST"])
def make_call():
    data = request.json
    to = data.get("to")
    script = data.get("script", "안녕하세요. 코코입니다.")

    response = requests.post(
        "https://api.claw-ops.com/v1/calls",
        headers={"Authorization": f"Bearer {CLAWOPS_API_KEY}"},
        json={
            "to": to,
            "from": CLAWOPS_FROM,
            "url": f"{BASE_URL}/twiml?script={requests.utils.quote(script)}",
            "account_id": CLAWOPS_ACCOUNT_ID,
        }
    )
    return response.json()

@app.route("/twiml", methods=["GET", "POST"])
def twiml():
    script = request.args.get("script", "안녕하세요. 코코입니다.")
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say language="ko-KR">{script}</Say>
</Response>"""
    return Response(xml, mimetype="text/xml")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)