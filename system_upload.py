import sqlite3
import time
import json
import ssl
import os
import sys
import paho.mqtt.client as mqtt

# ---------------- ENCODING ----------------
sys.stdout.reconfigure(encoding="utf-8")

# ---------------- BASE PATH ----------------
BASE_PATH = "/home/pi_123/data/src/pressure_project"

# ---------------- DATABASE ----------------
DB_PATH = os.path.join(BASE_PATH, "db", "project.db")

# ---------------- AWS CERTIFICATES ----------------
AWS_IOT_DIR = os.path.join(BASE_PATH, "aws_iot")

CERT_PATH = os.path.join(
    AWS_IOT_DIR,
    "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-certificate.pem.crt"
)
KEY_PATH = os.path.join(
    AWS_IOT_DIR,
    "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-private.pem.key"
)
CA_PATH = os.path.join(AWS_IOT_DIR, "AmazonRootCA1.pem")

# ---------------- VERIFY FILES ----------------
for f in [DB_PATH, CERT_PATH, KEY_PATH, CA_PATH]:
    if not os.path.exists(f):
        print("❌ Missing file:", f, flush=True)
        sys.exit(1)

print("✅ DB and certificate paths verified")

# ---------------- MQTT CONFIG ----------------
ENDPOINT  = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
PORT      = 8883
CLIENT_ID = "RaspberryPi_Pressure"
TOPIC     = "brake/pressure"

# ---------------- MQTT CALLBACKS ----------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core")
    else:
        print("❌ MQTT connect failed RC =", rc)

def on_publish(client, userdata, mid):
    print("📤 Data published")

# ---------------- CONNECT MQTT ----------------
def connect_mqtt():
    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_publish = on_publish

    client.tls_set(
        ca_certs=CA_PATH,
        certfile=CERT_PATH,
        keyfile=KEY_PATH,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )

    print("Connecting to AWS IoT Core...")
    client.connect(ENDPOINT, PORT, keepalive=60)
    client.loop_start()
    return client

mqtt_client = connect_mqtt()
time.sleep(2)

# ---------------- DATABASE CONNECT ----------------
conn = sqlite3.connect(DB_PATH, timeout=10)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# ---------------- UPLOAD FUNCTION ----------------
def upload_to_app(row):
    payload = {
        "id": row["id"],
        "bp": row["bp_pressure"],
        "fp": row["fp_pressure"],
        "cr": row["cr_pressure"],
        "bc": row["bc_pressure"],
        "timestamp": row["created_at"]
    }

    mqtt_client.publish(
        TOPIC,
        json.dumps(payload),
        qos=1
    )

    print(f"⬆️ Uploaded row {row['id']} → AWS")
    return True

# ---------------- MAIN LOOP ----------------
while True:
    cur.execute("""
        SELECT *
        FROM brake_pressure_log
        WHERE uploaded = 0
        ORDER BY created_at ASC
        LIMIT 1
    """)
    row = cur.fetchone()

    if row:
        if upload_to_app(row):
            cur.execute(
                "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                (row["id"],)
            )
            conn.commit()
            print(f"✅ Row {row['id']} marked uploaded")
    else:
        print("✅ No pending rows")

    time.sleep(5)
