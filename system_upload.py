import sqlite3
import time
import os
import sys
import json
import ssl
import paho.mqtt.client as mqtt

# ---------------- STDOUT ----------------
sys.stdout.reconfigure(encoding="utf-8")

# ---------------- BASE PATH ----------------
BASE_PATH = "/app" if os.path.exists("/app") else os.path.dirname(os.path.abspath(__file__))

# ---------------- DATABASE ----------------
DB_PATH = os.path.join(BASE_PATH, "db", "project.db")

# ---------------- AWS CERT PATHS (FIXED) ----------------
AWS_IOT_DIR = os.path.join(BASE_PATH, "aws_iot")

ROOT_CA = os.path.join(AWS_IOT_DIR, "AmazonRootCA1.pem")
CERT_FILE = os.path.join(
    AWS_IOT_DIR,
    "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-certificate.pem.crt"
)
KEY_FILE = os.path.join(
    AWS_IOT_DIR,
    "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-private.pem.key"
)

# ---------------- CHECK FILES ----------------
for f in [DB_PATH, ROOT_CA, CERT_FILE, KEY_FILE]:
    if not os.path.exists(f):
        print("❌ Missing file:", f, flush=True)
        sys.exit(1)

print("✅ Database and certificates verified", flush=True)

# ---------------- AWS SETTINGS ----------------
AWS_ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"  # <-- PUT YOUR ENDPOINT
AWS_PORT = 8883
CLIENT_ID = "Raspberry"
TOPIC = "brake/pressure"

# ---------------- DB CONNECTION ----------------
conn = sqlite3.connect(DB_PATH, timeout=10)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# ---------------- MQTT CALLBACK ----------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core", flush=True)
    else:
        print("❌ MQTT connection failed RC:", rc, flush=True)

# ---------------- MQTT CLIENT ----------------
client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
client.on_connect = on_connect

client.tls_set(
    ca_certs=ROOT_CA,
    certfile=CERT_FILE,
    keyfile=KEY_FILE,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

client.connect(AWS_ENDPOINT, AWS_PORT, 60)
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

    return result.rc == mqtt.MQTT_ERR_SUCCESS

# ---------------- MAIN LOOP ----------------
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
            print(f"⬆️ Uploaded & marked ID {row['id']}", flush=True)
        else:
            print("❌ Upload failed, retry later", flush=True)
            break

    time.sleep(2)
