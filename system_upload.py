import sqlite3
import time
import json
import ssl
import os
import paho.mqtt.client as mqtt

# ================= BASE PATH =================
BASE_PATH = "/app" if os.path.exists("/app") else os.path.dirname(os.path.abspath(__file__))

AWS_PATH = os.path.join(BASE_PATH, "aws_iot")
DB_PATH  = os.path.join(BASE_PATH, "db", "project.db")

# ================= FIND CERT FILES =================
def find_file(endswith):
    for f in os.listdir(AWS_PATH):
        if f.endswith(endswith):
            return os.path.join(AWS_PATH, f)
    return None

CA_PATH   = os.path.join(AWS_PATH, "AmazonRootCA1.pem")
CERT_PATH = find_file("-certificate.pem.crt")
KEY_PATH  = find_file("-private.pem.key")

# ================= VALIDATION =================
missing = []
if not os.path.exists(CA_PATH): missing.append("AmazonRootCA1.pem")
if not CERT_PATH: missing.append("Device Certificate")
if not KEY_PATH: missing.append("Private Key")

if missing:
    raise FileNotFoundError(f"Missing files: {', '.join(missing)}")

print("✅ All certificate files found")

# ================= MQTT CONFIG =================
ENDPOINT  = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
PORT      = 8883
CLIENT_ID = "Raspberry_pi"
TOPIC     = "raspi/brake/pressure"

# ================= CALLBACKS =================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core")
    else:
        print("❌ MQTT connection failed, RC =", rc)

def on_publish(client, userdata, mid):
    print("📤 Message published")

# ================= MQTT CONNECT =================
def connect_mqtt():
    print("🔄 Connecting to AWS IoT...")
    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
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

# ================= CONNECT =================
mqtt_client = None
while not mqtt_client:
    try:
        mqtt_client = connect_mqtt()
        time.sleep(2)
    except Exception as e:
        print("⚠️ MQTT error:", e)
        time.sleep(5)

# ================= DATABASE =================
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ================= UPLOAD FUNCTION =================
def upload_to_aws(row):
    payload = {
        "id": row["id"],
        "timestamp": row["created_at"],
        "bp_pressure": row["bp_pressure"],
        "fp_pressure": row["fp_pressure"],
        "cr_pressure": row["cr_pressure"],
        "bc_pressure": row["bc_pressure"]
    }

    result = mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)

    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(
            f"➡️ Uploaded | id={row['id']} | "
            f"BP={row['bp_pressure']} | "
            f"FP={row['fp_pressure']} | "
            f"CR={row['cr_pressure']} | "
            f"BC={row['bc_pressure']} | "
            f"time={row['created_at']}"
        )
        return True
    else:
        print("❌ Publish failed:", result.rc)
        return False

# ================= MAIN LOOP =================
while True:
    cursor.execute("""
        SELECT *
        FROM brake_pressure_log
        WHERE uploaded = 0
        ORDER BY created_at ASC
    """)
    rows = cursor.fetchall()

    if not rows:
        print("⏳ No pending rows. Waiting...")
        time.sleep(5)
        continue

    for row in rows:
        if upload_to_aws(row):
            cursor.execute(
                "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                (row["id"],)
            )
            conn.commit()
            print(f"✅ Marked uploaded | id={row['id']}")
        else:
            break

        time.sleep(2)
