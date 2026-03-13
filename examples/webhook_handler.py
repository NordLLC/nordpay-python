"""Webhook (postback) handler examples for FastAPI and Flask."""

# ---- FastAPI example ----

"""
from fastapi import FastAPI, Request, HTTPException
from nordpay.webhook import verify_postback
from nordpay.exceptions import WebhookVerificationError

app = FastAPI()
POSTBACK_SECRET = "your-postback-secret"

@app.post("/webhook/nordpay")
async def handle_postback(request: Request):
    body = await request.json()

    try:
        event = verify_postback(body, secret=POSTBACK_SECRET)
    except WebhookVerificationError:
        raise HTTPException(status_code=403, detail="Invalid postback secret")

    if event.postback_type == "transaction":
        print(f"Transaction {event.tx_hash}: {event.amount} {event.currency} — {event.status}")
    elif event.postback_type == "invoice_expired":
        print(f"Invoice #{event.object_id} expired")
    elif event.postback_type == "wallet_expired":
        print(f"Wallet #{event.object_id} expired")

    return {"ok": True}
"""


# ---- Flask example ----

"""
from flask import Flask, request, jsonify, abort
from nordpay.webhook import verify_postback
from nordpay.exceptions import WebhookVerificationError

app = Flask(__name__)
POSTBACK_SECRET = "your-postback-secret"

@app.route("/webhook/nordpay", methods=["POST"])
def handle_postback():
    try:
        event = verify_postback(request.json, secret=POSTBACK_SECRET)
    except WebhookVerificationError:
        abort(403)

    if event.postback_type == "transaction":
        print(f"Transaction {event.tx_hash}: {event.amount} {event.currency}")

    return jsonify(ok=True)
"""


# ---- Simple boolean check (no parsing) ----

"""
from nordpay.webhook import is_valid_postback

payload = {"postback_secret": "your-secret", "postback_type": "transaction", ...}
if is_valid_postback(payload, secret="your-secret"):
    # process event
    ...
"""
