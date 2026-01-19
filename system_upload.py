import sqlite3
import time
import json
import ssl
import os
import paho.mqtt.client as mqtt

# ---------------- PATH SETUP ----------------
BASE_PATH = "/app" if os.path.exists("/app") else os.path.dirname(os.path.abspath(__file__))
AWS_PATH = os.path.join(BASE_PATH, "aws_iot")
DB_PATH  = os.path.join(BASE_PATH, "db", "project.db")

CA_PATH   = os.path.join(AWS_PATH, "AmazonRootCA1.pem")
CERT_PATH = os.path.join(AWS_PATH, "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-certificate.pem.crt")
KEY_PATH  = os.path.join(AWS_PATH, "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-private.pem.key")

# ---------------- MQTT CONFIG ----------------
ENDPOINT  = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
PORT      = 8883
CLIENT_ID = "Raspberry"
TOPIC     = "brake/pressure"

# ---------------- MQTT CALLBACKS ----------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core")
    else:
        print("❌ MQTT connection failed, RC =", rc)

def on_publish(client, userdata, mid):
    print("📤 Data published")

# ---------------- CONNECT TO MQTT ----------------
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

# Wait until MQTT connects successfully
mqtt_client = None
while mqtt_client is None:
    try:
        mqtt_client = connect_mqtt()
    except Exception as e:
        print("❌ MQTT error:", e)
        time.sleep(5)

# ---------------- CONNECT TO DATABASE ----------------
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ---------------- FUNCTION TO UPLOAD ROW ----------------
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
        # Print full row info including sensor values
        print(
            f"➡️ Uploaded | id={row['id']} created_at={row['created_at']} | "
            f"BP={row['bp_pressure']} | FP={row['fp_pressure']} | "
            f"CR={row['cr_pressure']} | BC={row['bc_pressure']}"
        )
        return True
    else:
        print("❌ Publish failed:", result.rc)
        return False

# ---------------- MAIN LOOP ----------------
print("⏳ Starting uploader... checking for pending rows every 5 seconds.\n")

while True:
    try:
        # Fetch pending rows ordered by timestamp (oldest first)
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
                print("❌ Upload failed, will retry later.")
                break

            # Mark row as uploaded after successful publish
            cursor.execute(
                "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                (row["id"],)
            )
            conn.commit()
            print(f"✅ Marked uploaded | id={row['id']} created_at={row['created_at']}")

            time.sleep(2)  # small delay between uploads

    except KeyboardInterrupt:
        print("\n🛑 Exiting uploader.")
        break
    except Exception as e:
        print("❌ Error:", e)
        time.sleep(5)
