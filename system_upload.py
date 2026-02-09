import json
import time
import ssl
import sqlite3
from datetime import datetime
import paho.mqtt.client as mqtt

# ---------------- CONFIG ----------------
AWS_ENDPOINT = "xxxxxxxxxxxxx-ats.iot.ap-south-1.amazonaws.com"
PORT = 8883
TOPIC = "pressure/data"

CLIENT_ID = "Raspberry_pi"

CA_PATH   = "certs/AmazonRootCA1.pem"
CERT_PATH = "certs/device.pem.crt"
KEY_PATH  = "certs/private.pem.key"

DB_PATH = "data/pressure.db"

# ----------------------------------------

def get_pending_row():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, created_at, bp, bc, cr, fp
        FROM pressure_log
        WHERE uploaded = 0
        ORDER BY id ASC
        LIMIT 1
    """)

    row = cur.fetchone()
    conn.close()
    return row


def mark_uploaded(row_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE pressure_log SET uploaded = 1 WHERE id = ?", (row_id,))
    conn.commit()
    conn.close()


# ---------------- MQTT CALLBACKS ----------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ AWS IoT Connected")
    else:
        print(f"❌ Connection failed rc={rc}")


def on_disconnect(client, userdata, rc):
    print("⚠️ MQTT Disconnected, reconnecting...")
    time.sleep(5)
    try:
        client.reconnect()
    except Exception as e:
        print("Reconnect failed:", e)


# ---------------- MQTT SETUP ----------------
client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
client.on_connect = on_connect
client.on_disconnect = on_disconnect

client.tls_set(
    ca_certs=CA_PATH,
    certfile=CERT_PATH,
    keyfile=KEY_PATH,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

client.connect(AWS_ENDPOINT, PORT)
client.loop_start()

# ---------------- MAIN LOOP ----------------
while True:
    try:
        row = get_pending_row()

        if not row:
            time.sleep(2)
            continue

        row_id, ts, bp, bc, cr, fp = row

        payload = {
            "id": row_id,
            "timestamp": ts,
            "bp": bp,
            "bc": bc,
            "cr": cr,
            "fp": fp
        }

        client.publish(TOPIC, json.dumps(payload), qos=1)

        print(
            f"✅ Uploaded | id={row_id} timestamp={ts} "
            f"bp={bp} bc={bc} cr={cr} fp={fp}"
        )
        print(f"📤 AWS IoT Sent: {json.dumps(payload)}")

        mark_uploaded(row_id)

    except Exception as e:
        print("❌ Upload error:", e)

    time.sleep(1)
