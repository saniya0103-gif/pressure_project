import sqlite3
import time
import json
import ssl
import os
import gc
import paho.mqtt.client as mqtt

# ---------------- BASE PATH ----------------
BASE_PATH = "/app" if os.path.exists("/app") else os.path.dirname(os.path.abspath(__file__))

AWS_PATH = os.path.join(BASE_PATH, "aws_iot")
DB_PATH  = os.path.join(BASE_PATH, "db", "project.db")

# ---------------- CERT PATHS ----------------
CA_PATH   = os.path.join(AWS_PATH, "AmazonRootCA1.pem")
CERT_PATH = os.path.join(AWS_PATH, "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-certificate.pem.crt")
KEY_PATH  = os.path.join(AWS_PATH, "c5811382f2c2cfb311d53c99b4b0fadf4889674d-private.pem.key")

# ---------------- VERIFY FILES ----------------
for name, path in {
    "CA": CA_PATH,
    "CERT": CERT_PATH,
    "KEY": KEY_PATH,
    "DB": DB_PATH
}.items():
    if not os.path.exists(path):
        raise FileNotFoundError(f"{name} not found: {path}")

print("✅ All certificate files found", flush=True)

# ---------------- MQTT CONFIG ----------------
ENDPOINT  = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
PORT      = 8883
CLIENT_ID = "Raspberry"
TOPIC     = "brake/pressure"

# ---------------- MQTT CALLBACKS ----------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core", flush=True)
    else:
        print("❌ MQTT connect failed:", rc, flush=True)

def on_publish(client, userdata, mid):
    print("📤 Message published", flush=True)

# ---------------- MQTT CONNECT ----------------
def connect_mqtt():
    print("🔄 Connecting to AWS IoT...", flush=True)

    client = mqtt.Client(
        client_id=CLIENT_ID,
        protocol=mqtt.MQTTv311
    )

    client.on_connect = on_connect
    client.on_publish = on_publish

    client.tls_set(
        ca_certs=CA_PATH,
        certfile=CERT_PATH,
        keyfile=KEY_PATH,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )

    client.connect(ENDPOINT, PORT, keepalive=60)
    client.loop_start()
    return client

mqtt_client = None
while mqtt_client is None:
    try:
        mqtt_client = connect_mqtt()
    except Exception as e:
        print("❌ MQTT error:", e, flush=True)
        time.sleep(5)

# ---------------- DATABASE ----------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ---------------- UPLOAD FUNCTION ----------------
def upload_to_aws(row):
    payload = {
        "id": row["id"],
        "timestamp": row["created_at"],
        "bp": row["bp_pressure"],
        "fp": row["fp_pressure"],
        "cr": row["cr_pressure"],
        "bc": row["bc_pressure"]
    }

    result = mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)

    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(
            f"➡️ Uploaded | id={row['id']} | "
            f"BP={row['bp_pressure']} | "
            f"FP={row['fp_pressure']} | "
            f"CR={row['cr_pressure']} | "
            f"BC={row['bc_pressure']} | "
            f"time={row['created_at']}",
            flush=True
        )
        gc.collect()
        return True
    else:
        print("❌ Publish failed:", result.rc, flush=True)
        return False

# ---------------- MAIN LOOP ----------------
while True:
    cursor.execute("""
        SELECT * FROM brake_pressure_log
        WHERE uploaded = 0
        ORDER BY created_at ASC
    """)
    rows = cursor.fetchall()

    if not rows:
        print("⏳ No pending rows. Waiting...", flush=True)
        gc.collect()
        time.sleep(10)
        continue

    for row in rows:
        success = upload_to_aws(row)
        if not success:
            break

        cursor.execute(
            "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
            (row["id"],)
        )
        conn.commit()

        print(f"✅ Marked uploaded | id={row['id']}", flush=True)
        gc.collect()
        time.sleep(10)
