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

CA_PATH   = os.path.join(AWS_PATH, "AmazonRootCA1.pem")
CERT_PATH = os.path.join(AWS_PATH, "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-certificate.pem.crt")
KEY_PATH  = os.path.join(AWS_PATH, "c5811382f2c2cfb311d53c99b4b0fadf4889674d-private.pem.key")

# ================= CHECK FILES =================
for name, path in {
    "DB": DB_PATH,
    "CA": CA_PATH,
    "CERT": CERT_PATH,
    "KEY": KEY_PATH
}.items():
    if not os.path.exists(path):
        raise FileNotFoundError(f"{name} not found: {path}")

print("✅ All certificate files found")

# ================= MQTT CONFIG =================
ENDPOINT  = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
PORT      = 8883
CLIENT_ID = "Raspberry_pi"          # MUST match IoT policy
TOPIC     = "raspi/brake/pressure"   # MUST match IoT policy

mqtt_connected = False

# ================= CALLBACKS =================
def on_connect(client, userdata, flags, rc):
    global mqtt_connected
    if rc == 0:
        mqtt_connected = True
        print("✅ Connected to AWS IoT Core")
    else:
        print("❌ MQTT connect failed. RC =", rc)

def on_disconnect(client, userdata, rc):
    print("🔌 Disconnected (rc =", rc, ")")

def on_publish(client, userdata, mid):
    print("📤 Message published")

# ================= MQTT CONNECT =================
def connect_mqtt():
    print("🔄 Connecting to AWS IoT...")
    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish

    client.tls_set(
        ca_certs=CA_PATH,
        certfile=CERT_PATH,
        keyfile=KEY_PATH,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )

    client.connect(ENDPOINT, PORT, keepalive=60)
    client.loop_start()

    while not mqtt_connected:
        time.sleep(0.5)

    return client

mqtt_client = connect_mqtt()

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
    result.wait_for_publish()

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

    print("❌ Publish failed, rc =", result.rc)
    return False

# ================= MAIN LOOP =================
print("🚀 Upload service started")

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
            print("⚠ Upload failed, retry later")
            break

        time.sleep(2)
