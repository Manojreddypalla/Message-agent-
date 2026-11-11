import time
import qrcode
import ollama
from neonize.client import NewClient
from neonize.events import MessageEv, ConnectedEv, QREv

# Local Ollama client running on your RTX 4060 GPU
ollama_client = ollama.Client(host="http://localhost:11434")
MODEL_NAME = "llama3.1:8b"

SYSTEM_PROMPT = (
    "You are a friendly, expert personal trainer for Iron Pulse Gym. "
    "Keep answers concise, motivating, structured with bullet points, and formatted for WhatsApp."
)

# Local session file so you only scan the QR code once
client = NewClient("gym_bot_session.sqlite3")

@client.event(QREv)
def on_qr(client: NewClient, qr_data: bytes):
    """Prints the QR code in terminal if re-authentication is needed."""
    print("\n📱 SCAN THIS QR CODE WITH PHONE A (WhatsApp > Linked Devices):\n")
    qr = qrcode.QRCode()
    qr.add_data(qr_data)
    qr.print_ascii(invert=True)

@client.event(ConnectedEv)
def on_connected(client: NewClient, event: ConnectedEv):
    print("\n✅ Phone A is officially CONNECTED to your RTX 4060! Listening for messages...\n")

@client.event(MessageEv)
def on_message(client: NewClient, message: MessageEv):
    # Extract text from incoming WhatsApp message
    msg_text = (
        message.Message.conversation
        or (message.Message.extendedTextMessage.text if message.Message.extendedTextMessage else "")
    )

    if not msg_text:
        return

    print(f"📩 Incoming message: '{msg_text}'")

    # Generate reply locally on your RTX 4060 GPU
    try:
        response = ollama_client.chat(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": msg_text},
            ],
            options={"temperature": 0.7},
        )
        reply = response["message"]["content"]
        print(f"🤖 RTX 4060 replied:\n{reply}\n")

        # Send reply back to WhatsApp (text first, then message object)
        try:
            client.reply_message(reply, message)
        except Exception:
            client.send_message(message.Info.MessageSource.Chat, reply)

    except Exception as e:
        print(f"Error during LLM inference: {e}")

print("🚀 Starting Gym AI Bot...")
client.connect()

# Keep script running permanently so Python doesn't exit
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopping bot...")