import sqlite3
import json
import time
import os
import ssl
import paho.mqtt.client as mqtt

# ===================== BASE PATH =====================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "project.db")

CERT_DIR = os.path.join(BASE_DIR, "aws_iot")

ROOT_CA = os.path.join(CERT_DIR, "AmazonRootCA1.pem")
CERT_FILE = os.path.join(CERT_DIR, "device.pem.crt")
KEY_FILE = os.path.join(CERT_DIR, "private.pem.key")

# ===================== AWS CONFIG =====================
AWS_ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
PORT      = 8883
CLIENT_ID = "Raspberry"
TOPIC = "brake/pressure"

# ===================== SAFE PATH CHECK (NO CRASH) =====================
print("Checking DB & certificate paths...")

if not os.path.exists(DB_PATH):
    print("❌ Database not found:", DB_PATH)

if not os.path.exists(ROOT_CA):
    print("⚠ Root CA missing:", ROOT_CA)

if not os.path.exists(CERT_FILE):
    print("⚠ Device certificate missing:", CERT_FILE)

if not os.path.exists(KEY_FILE):
    print("⚠ Private key missing:", KEY_FILE)

print("✅ Path check completed (no forced stop)")

# ===================== MQTT SETUP =====================
client = mqtt.Client(client_id=CLIENT_ID)

client.tls_set(
    ca_certs=ROOT_CA,
    certfile=CERT_FILE,
    keyfile=KEY_FILE,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

client.tls_insecure_set(False)

# ===================== CALLBACK =====================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core")
    else:
        print("❌ AWS IoT connection failed, rc =", rc)

client.on_connect = on_connect

print("Connecting to AWS IoT Core...")
client.connect(AWS_ENDPOINT, 8883)
client.loop_start()

# ===================== DATABASE =====================
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# ===================== MAIN LOOP =====================
while True:
    cur.execute("""
        SELECT *
        FROM brake_pressure_log
        WHERE uploaded = 0
        ORDER BY created_at ASC
        LIMIT 5
    """)
    rows = cur.fetchall()

    if not rows:
        print("✅ No pending rows")
        time.sleep(5)
        continue

    for row in rows:
        payload = {
            "created_at": row["created_at"],
            "bp_pressure": row["bp_pressure"],
            "fp_pressure": row["fp_pressure"],
            "cr_pressure": row["cr_pressure"],
            "bc_pressure": row["bc_pressure"],
            "aws_status": "uploaded"
        }

        payload_json = json.dumps(payload)

        result = client.publish(TOPIC, payload_json, qos=1)

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print("Sent to AWS IoT:", payload)

            cur.execute(
                "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                (row["id"],)
            )
            conn.commit()

            print(
                f"Uploaded and marked DB uploaded=1 | "
                f"Timestamp: {row['created_at']}"
            )
            print("Data published to AWS IoT\n")

        else:
            print("❌ Publish failed, retry later")
            break

    time.sleep(2)
