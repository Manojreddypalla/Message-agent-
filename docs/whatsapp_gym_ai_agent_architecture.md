---
title: WhatsApp Gym AI Agent - Architecture & Implementation Guide
tags:
  - ai-agent
  - whatsapp
  - llm
  - ollama
  - rtx4060
  - python
  - fastapi
  - internship
created: 2026-11-11
author: Manoj Reddy
project: Iron Pulse Gym WhatsApp AI
---

# WhatsApp Gym AI Agent: Architecture & Implementation Notes

> [!abstract] Executive Summary
> This note documents the end-to-end architecture, developer workflow, and production migration roadmap for the **Iron Pulse Gym WhatsApp AI Assistant**. It covers rapid zero-cost developer testing using a dual-phone local bridge (`neonize` + local RTX 4060 GPU with Ollama) and an adapter pattern for seamless future migration to the official **Meta WhatsApp Cloud API**.

---

## 1. High-Level System Architecture

The system decouples the **Messaging Gateway** from the **AI Business Core**, allowing the messaging layer to be swapped between developer testing and production without touching agent logic.

```text
+-------------------------------------------------------------------------+
|                           MESSAGING GATEWAY LAYER                       |
|                                                                         |
|  [Dev Testing: bot_qr.py]                     [Production: bot_meta.py] |
|  - Uses neonize (WhatsApp Web socket)         - Uses FastAPI Webhook    |
|  - Authenticated via QR scan on Phone A       - Official Meta Cloud API |
|  - Zero third-party fees                      - 24/7 server, unbannable |
+------------------------------------+------------------------------------+
                                     | Passes (sender_phone, text)
                                     v
+-------------------------------------------------------------------------+
|                        CORE AI AGENT (agent.py)                         |
|                                                                         |
|  1. Calls database.py to check member status (Active Member vs Lead)    |
|  2. Injects member profile & gym rules into system prompt               |
|  3. Runs local GPU inference on NVIDIA RTX 4060 via Ollama              |
|  4. Returns structured payload: { "text": "...", "image": "..." }       |
+------------------------------------+------------------------------------+
                                     |
                                     v
+-------------------------------------------------------------------------+
|                         DATA & STORAGE LAYER                            |
|                                                                         |
|  - Dev: In-memory dictionary / SQLite (database.py)                     |
|  - Production: MongoDB / PostgreSQL + Redis / Qdrant Vector DB          |
+-------------------------------------------------------------------------+
```

---

## 2. Comparing the Two Workflows

| Evaluation Metric | Developer Testing (Current QR Bot) | Enterprise Production (Official Meta API) |
| :--- | :--- | :--- |
| **Mechanism** | Reverse-engineered Multi-Device WebSocket (`neonize` / whatsmeow) | Official REST Webhook & Graph API (`graph.facebook.com`) |
| **Account Type** | Personal WhatsApp SIM (Phone A) | Verified Meta Business Portfolio & dedicated number |
| **Cost** | 100% Free | Pay-as-you-go (~1,000 free conversations/month) |
| **Hardware Host** | Local laptop/PC with physical phone connected | Headless Linux Cloud VM (AWS, DigitalOcean, Render) |
| **Ban Risk** | **High** if scaled to hundreds of daily messages | **Zero** (100% compliant with Meta Business Policies) |
| **Session Lifetime** | Must re-scan QR if phone restarts or drops net | Permanent; token-based authentication |
| **Concurrency** | Sequential single-socket stream | Hundreds of concurrent requests per second |
| **Branding** | Ordinary personal phone number | Verified Business Profile, Green Tick, Gym Logo |

> [!warning] Production Risk Warning
> Unofficial WhatsApp Web scrapers/sockets (`neonize`, `whatsapp-web.js`) will result in permanent SIM card bans if used to broadcast bulk notifications or answer hundreds of concurrent customers. Always switch to Meta Cloud API for real gym members.

---

## 3. Project Directory Structure

```text
Message-agent/
│
├── .env                  # Secrets & configuration (tokens, model name, ports)
├── requirements.txt      # Python dependencies
├── database.py           # Data access layer (member lookup & visit logging)
├── agent.py              # Central intelligence (prompts, Ollama, tools)
├── bot_qr.py             # Active runner for local developer testing (Neonize)
└── bot_meta.py           # Ready-to-use runner for official Meta Cloud API
```

---

## 4. Complete Code Implementation

### A. Data Layer: `database.py`
> [!note] Swappable Storage
> In production, replace `MEMBERS_TABLE` with queries to MongoDB or PostgreSQL.

```python
from datetime import datetime

MEMBERS_TABLE = {
    "919876543210": {
        "name": "Manoj Reddy",
        "plan": "Gold Annual",
        "expiry": "2026-12-31",
        "fee_due": 0,
        "trainer": "Coach Vikram",
        "goal": "Muscle Hypertrophy",
    },
    "919123456789": {
        "name": "Rahul Sharma",
        "plan": "Monthly",
        "expiry": "2026-11-05",
        "fee_due": 1500,
        "trainer": "General Staff",
        "goal": "Fat Loss & Endurance",
    },
}

def get_member_by_phone(phone: str) -> dict:
    """Sanitizes phone number and returns member profile if registered."""
    clean_phone = phone.replace("+", "").replace("whatsapp:", "").strip()
    return MEMBERS_TABLE.get(clean_phone)

def record_gym_visit(phone: str):
    """Updates member attendance timestamp."""
    clean_phone = phone.replace("+", "").replace("whatsapp:", "").strip()
    if clean_phone in MEMBERS_TABLE:
        MEMBERS_TABLE[clean_phone]["last_visit"] = datetime.now().strftime("%Y-%m-%d")
```

---

### B. Core AI Agent: `agent.py`
> [!tip] Isolated Logic
> This file contains zero messaging code. It can be called by CLI, Webhook, QR socket, or Discord.

```python
import ollama
from database import get_member_by_phone

ollama_client = ollama.Client(host="http://localhost:11434")
MODEL_NAME = "llama3.1:8b"

GYM_INFO = {
    "name": "Iron Pulse Gym",
    "timing": "Mon-Sat: 6:00 AM - 10:00 PM | Sun: 7:00 AM - 1:00 PM",
    "location": "Road No. 36, Jubilee Hills, Hyderabad",
    "plans": "Monthly: Rs 1,500 | Quarterly: Rs 4,000 | Annual (Gold): Rs 12,000",
}

def generate_gym_response(sender_phone: str, user_message: str) -> dict:
    member = get_member_by_phone(sender_phone)

    # 1. Branching based on member registration
    if member:
        user_context = (
            f"Active Member: {member['name']}\n"
            f"Plan: {member['plan']} (Valid until {member['expiry']})\n"
            f"Outstanding Fee: Rs {member['fee_due']}\n"
            f"Assigned Trainer: {member['trainer']}\n"
            f"Fitness Goal: {member['goal']}"
        )
    else:
        user_context = (
            "Prospective Visitor (Unregistered Lead).\n"
            f"Timings: {GYM_INFO['timing']}\n"
            f"Location: {GYM_INFO['location']}\n"
            f"Plans: {GYM_INFO['plans']}\n"
            "Be welcoming and offer a free 1-day workout trial pass."
        )

    # 2. System Instructions
    system_prompt = (
        f"You are the virtual personal trainer for {GYM_INFO['name']}.\n"
        f"{user_context}\n\n"
        "GUIDELINES:\n"
        "- Address registered members by their name.\n"
        "- If they ask about workouts, tailor sets/reps to their fitness goal.\n"
        "- If weight (kg) and height (cm) are given, calculate BMI: weight / (height_in_m ^ 2).\n"
        "- Format answers with bullet points and emojis for mobile WhatsApp screens."
    )

    # 3. Local GPU Inference (RTX 4060)
    response = ollama_client.chat(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        options={"temperature": 0.7},
    )
    reply_text = response["message"]["content"]

    # Optional image routing (diet chart, workout plan infographics)
    image_file = None
    if any(k in user_message.lower() for k in ["diet", "chart", "meal plan"]):
        image_file = "assets/diet_chart.jpg"

    return {"text": reply_text, "image": image_file}
```

---

### C. Testing Runner: `bot_qr.py` (Local Dual-Phone Setup)

```python
import time
import qrcode
from neonize.client import NewClient
from neonize.events import MessageEv, ConnectedEv, QREv
from agent import generate_gym_response

client = NewClient("gym_bot_session.sqlite3")

@client.event(QREv)
def on_qr(client: NewClient, qr_data: bytes):
    print("\n[!] Scan this QR code with Phone A (WhatsApp > Linked Devices):\n")
    qr = qrcode.QRCode()
    qr.add_data(qr_data)
    qr.print_ascii(invert=True)

@client.event(ConnectedEv)
def on_connected(client: NewClient, event: ConnectedEv):
    print("\n[+] Phone A linked! Listening for incoming WhatsApp messages...\n")

@client.event(MessageEv)
def on_message(client: NewClient, message: MessageEv):
    msg_text = (
        message.Message.conversation
        or (message.Message.extendedTextMessage.text if message.Message.extendedTextMessage else "")
    )
    if not msg_text:
        return

    sender = message.Info.MessageSource.Sender.User
    print(f"[*] Incoming from {sender}: {msg_text}")

    result = generate_gym_response(sender_phone=sender, user_message=msg_text)
    print(f"[>] Reply:\n{result['text']}\n")

    # Send text reply (text first, message event second)
    try:
        client.reply_message(result["text"], message)
    except Exception:
        client.send_message(message.Info.MessageSource.Chat, result["text"])

print("[*] Starting WhatsApp client...")
client.connect()

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n[!] Shutting down.")
```

---

### D. Production Runner: `bot_meta.py` (Official Cloud API)

```python
import os
import requests
from fastapi import FastAPI, Request
from agent import generate_gym_response

app = FastAPI(title="Iron Pulse Gym - WhatsApp Production API")

PHONE_NUMBER_ID = os.getenv("META_PHONE_NUMBER_ID")
ACCESS_TOKEN = os.getenv("META_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("META_VERIFY_TOKEN", "ironpulse_secret_token")

@app.get("/webhook")
def verify_meta_webhook(request: Request):
    params = request.query_params
    if params.get("hub.mode") == "subscribe" and params.get("hub.verify_token") == VERIFY_TOKEN:
        return int(params.get("hub.challenge"))
    return "Verification failed", 403

@app.post("/webhook")
async def receive_meta_event(request: Request):
    body = await request.json()
    try:
        msg = body["entry"][0]["changes"][0]["value"]["messages"][0]
        sender = msg["from"]
        text = msg.get("text", {}).get("body", "")

        # Call the EXACT SAME agent function
        result = generate_gym_response(sender_phone=sender, user_message=text)

        # Dispatch via Meta Graph API
        url = f"https://graph.facebook.com/v20.0/{PHONE_NUMBER_ID}/messages"
        headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
        payload = {
            "messaging_product": "whatsapp",
            "to": sender,
            "type": "text",
            "text": {"body": result["text"]},
        }
        requests.post(url, headers=headers, json=payload)
    except Exception as e:
        print(f"Error handling message: {e}")

    return {"status": "success"}
```

---

## 5. Troubleshooting Reference

> [!check] Common Developer Errors & Fixes
> - **`VersionError: Detected incompatible Protobuf Gencode/Runtime`**:
>   - *Cause*: `neonize` requires a newer version of Google's protobuf runtime.
>   - *Fix*: Run `pip install --upgrade protobuf`.
> - **`Error: 'str' object has no attribute 'Info'`**:
>   - *Cause*: `client.reply_message()` was called with reversed arguments (`message, reply`).
>   - *Fix*: Call `client.reply_message(reply, message)` (string text first, message object second).
> - **Script exits immediately with zero output**:
>   - *Cause*: `client.connect()` runs in a background Go routine, allowing Python's main thread to exit.
>   - *Fix*: Keep the thread alive with a `while True: time.sleep(1)` loop.
> - **Meta Developer "Your advertising access is restricted"**:
>   - *Cause*: Automated policy flag on personal Facebook ad account blocking Business Portfolio creation.
>   - *Fix*: Use the two-phone QR bridge (`bot_qr.py`) for development; have the gym manager add you to the gym's verified business portfolio for production.

---

## 6. Large-Scale Production Scaling Roadmap

1. **Step 1: Dedicated Number Provisioning**
   - Procure a clean dedicated SIM for the gym.
   - Register the number inside Meta Business Suite via Embedded Signup.
2. **Step 2: Cloud Host Deployment**
   - Deploy `bot_meta.py` on AWS EC2 or DigitalOcean Droplet ($6/mo).
   - Terminate SSL via Caddy/Nginx to provide a static HTTPS webhook URL.
3. **Step 3: Inference Scaling**
   - For low volume (<20 concurrent users): Self-host open-source models using `vLLM` or local GPU server.
   - For high volume: Point agent reasoning to `gemini-2.5-flash` API for infinite scale and sub-second responses.
4. **Step 4: Persistent Memory & CRM Sync**
   - Connect `database.py` to the gym's real membership management CRM (PostgreSQL / MongoDB).
   - Integrate vector storage (`Qdrant` + `Mem0`, matching the Robin multi-agent architecture) for cross-session conversational memory.