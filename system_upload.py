import sqlite3
import time
import json
import ssl
import os
import paho.mqtt.client as mqtt

# ---------------- DEBUG ----------------
print("=== DEBUG START ===", flush=True)
print("PWD:", os.getcwd(), flush=True)
print("List /app:", os.listdir("/app"), flush=True)
print("List /app/aws_iot:", os.listdir("/app/aws_iot"), flush=True)

# ---------------- PATHS ----------------
paths = {
    "DB": "/app/db/project.db",
    "CA": "/app/aws_iot/AmazonRootCA1.pem",
    "CERT": "/app/aws_iot/c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-certificate.pem.crt",
    "KEY": "/app/aws_iot/c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-private.pem.key"
}

for name, path in paths.items():
    print(f"{name} exists:", os.path.exists(path), path, flush=True)

print("=== DEBUG END ===", flush=True)

DB_PATH   = paths["DB"]
CA_PATH   = paths["CA"]
CERT_PATH = paths["CERT"]
KEY_PATH  = paths["KEY"]

# ---------------- MQTT CONFIG ----------------
ENDPOINT  = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
PORT      = 8883
CLIENT_ID = "Raspberry"
TOPIC     = "brake/pressure"

# ---------------- CALLBACKS ----------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core")
    else:
        print("❌ MQTT connection failed, RC =", rc)

def on_publish(client, userdata, mid):
    print("📤 Data published")

# ---------------- MQTT CONNECT ----------------
def connect_mqtt():
    print("🔄 Connecting to AWS IoT...")
    client = mqtt.Client(
        client_id=CLIENT_ID,
        protocol=mqtt.MQTTv311,
        transport="tcp"
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

# ---------------- WAIT FOR MQTT ----------------
mqtt_client = None
while mqtt_client is None:
    try:
        mqtt_client = connect_mqtt()
    except Exception as e:
        print("❌ MQTT error:", e)
        time.sleep(5)

# ---------------- DATABASE ----------------
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ---------------- UPLOAD FUNCTION ----------------
def upload_to_aws(row):
    payload = {
        "created_at": row["created_at"],
        "bp_pressure": row["bp_pressure"],
        "fp_pressure": row["fp_pressure"],
        "cr_pressure": row["cr_pressure"],
        "bc_pressure": row["bc_pressure"],
        "db_uploaded": row["uploaded"],
        "aws_status": "uploaded"
    }

    result = mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)

    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print("➡️ Sent:", payload)
    else:
        print("❌ Publish failed:", result.rc)

# ---------------- MAIN LOOP ----------------
while True:
    cursor.execute("""
        SELECT * FROM brake_pressure_log
        WHERE uploaded = 0
        ORDER BY created_at ASC
    """)
    rows = cursor.fetchall()

    if not rows:
        print("No pending rows. Waiting...")
        time.sleep(15)
        continue

    for row in rows:
        upload_to_aws(row)

        cursor.execute(
            "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
            (row["id"],)
        )
        conn.commit()

        print(f"✅ Marked uploaded | {row['created_at']}")
        time.sleep(10)
