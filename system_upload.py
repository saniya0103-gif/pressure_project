import sqlite3
import time
import json
import ssl
import os
import paho.mqtt.client as mqtt

# ---------------- DYNAMIC BASE PATH ----------------
# Use /app if inside Docker, otherwise use host project folder
BASE_PATH = "/app" if os.path.exists("/app") else os.path.dirname(os.path.abspath(__file__))

# ---------------- DEBUG ----------------
print("=== DEBUG START ===", flush=True)
print("PWD:", BASE_PATH, flush=True)

AWS_PATH = os.path.join(BASE_PATH, "aws_iot")
DB_PATH  = os.path.join(BASE_PATH, "db", "project.db")

# List folder contents safely
print("List BASE_PATH:", os.listdir(BASE_PATH), flush=True)
if os.path.exists(AWS_PATH):
    print("List AWS_PATH:", os.listdir(AWS_PATH), flush=True)
else:
    print("AWS folder not found:", AWS_PATH, flush=True)

# Paths
paths = {
    "DB": DB_PATH,
    "CA": os.path.join(AWS_PATH, "AmazonRootCA1.pem"),
    "CERT": os.path.join(AWS_PATH, "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-certificate.pem.crt"),
    "KEY": os.path.join(AWS_PATH, "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-private.pem.key")
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
# Ensure DB folder exists
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

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
        return True 
    else:
        print("❌ Publish failed:", result.rc)
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
        print("No pending rows. Waiting...")
        time.sleep(5)
        continue

    for row in rows:
        success = upload_to_aws(row)
        if not success:
            print("Upload failed, will retry later.")
            break
        time.sleep(2)  # keep your original sleep condition

        cursor.execute(
            "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
            (row["id"],)
        )
        conn.commit()

        print(f"Marked uploaded | {row['created_at']}")
