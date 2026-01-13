import sqlite3
import time
import json
import ssl
import paho.mqtt.client as mqtt

# ---------------- PATHS (INSIDE DOCKER) ----------------
DB_PATH = "/app/project.db"

CERT_PATH = "/app/aws_iot/c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-certificate.pem.crt"
KEY_PATH  = "/app/aws_iot/c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-private.pem.key"
CA_PATH   = "/app/aws_iot/AmazonRootCA1.pem"

# ---------------- MQTT CONFIG ----------------
ENDPOINT  = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
PORT      = 8883
CLIENT_ID = "pressure-uploader"
TOPIC     = "brake/pressure"

# ---------------- MQTT CALLBACKS ----------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core")
    else:
        print("❌ MQTT connection failed, RC =", rc)

def on_publish(client, userdata, mid):
    print("📤 Data published to AWS IoT")

# ---------------- MQTT CONNECT ----------------
def connect_mqtt():
    client = mqtt.Client(client_id=CLIENT_ID)
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
        print("MQTT error:", e)
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

    mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)
    print("➡️ Sent:", payload)

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
