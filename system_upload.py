import sqlite3
import time
import os
import sys
import json
import ssl
import paho.mqtt.client as mqtt

# ---------------- STDOUT ----------------
sys.stdout.reconfigure(encoding="utf-8")

# ---------------- PATHS ----------------
BASE_PATH = "/app" if os.path.exists("/app") else os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_PATH, "db", "project.db")
AWS_PATH = os.path.join(BASE_PATH, "aws_iot")

ROOT_CA = os.path.join(AWS_PATH, "AmazonRootCA1.pem")
CERT_FILE = os.path.join(AWS_PATH, "device.pem.crt")
KEY_FILE = os.path.join(AWS_PATH, "private.pem.key")

# ---------------- AWS SETTINGS ----------------
AWS_ENDPOINT = "xxxxxxxxxxxx-ats.iot.ap-south-1.amazonaws.com"  # <-- CHANGE
AWS_PORT = 8883
CLIENT_ID = "pressure_pi_01"
TOPIC = "railway/brake_pressure"

# ---------------- VALIDATE FILES ----------------
for f in [DB_PATH, ROOT_CA, CERT_FILE, KEY_FILE]:
    if not os.path.exists(f):
        print("❌ Missing file:", f, flush=True)
        sys.exit(1)

print("✅ All paths verified", flush=True)

# ---------------- DB CONNECTION ----------------
conn = sqlite3.connect(DB_PATH, timeout=10)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# ---------------- MQTT CALLBACKS ----------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core", flush=True)
    else:
        print("❌ MQTT connection failed, RC:", rc, flush=True)

# ---------------- MQTT CLIENT ----------------
client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
client.on_connect = on_connect

client.tls_set(
    ca_certs=ROOT_CA,
    certfile=CERT_FILE,
    keyfile=KEY_FILE,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

client.connect(AWS_ENDPOINT, AWS_PORT, keepalive=60)
client.loop_start()

# ---------------- UPLOAD FUNCTION ----------------
def upload_to_aws(row):
    payload = {
        "id": row["id"],
        "bp": row["bp_pressure"],
        "fp": row["fp_pressure"],
        "cr": row["cr_pressure"],
        "bc": row["bc_pressure"],
        "timestamp": row["created_at"]
    }

    result = client.publish(TOPIC, json.dumps(payload), qos=1)
    result.wait_for_publish()

    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(f"⬆️ Uploaded ID {row['id']}", flush=True)
        return True
    else:
        print("❌ Publish failed", flush=True)
        return False

# ---------------- MAIN LOOP ----------------
while True:
    try:
        cur.execute("""
            SELECT *
            FROM brake_pressure_log
            WHERE uploaded = 0
            ORDER BY created_at ASC
            LIMIT 5
        """)
        rows = cur.fetchall()

        if not rows:
            print("✅ No pending rows", flush=True)
            time.sleep(5)
            continue

        for row in rows:
            if upload_to_aws(row):
                cur.execute(
                    "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                    (row["id"],)
                )
                conn.commit()
                print(f"✅ Row {row['id']} marked uploaded (1)", flush=True)
            else:
                break

        time.sleep(2)

    except Exception as e:
        print("❌ Error:", e, flush=True)
        time.sleep(5)
