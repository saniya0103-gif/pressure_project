import sqlite3
import time
import json
import ssl
import os
import paho.mqtt.client as mqtt

# ---------------- DYNAMIC BASE PATH ----------------
BASE_PATH = "/app" if os.path.exists("/app") else os.path.dirname(os.path.abspath(__file__))
AWS_PATH  = os.path.join(BASE_PATH, "aws_iot")
DB_PATH   = os.path.join(BASE_PATH, "db", "project.db")

# ---------------- DEBUG ----------------
print("=== DEBUG START ===", flush=True)
print("BASE_PATH:", BASE_PATH, flush=True)
print("AWS_PATH:", AWS_PATH, flush=True)
print("DB_PATH:", DB_PATH, flush=True)

if not os.path.exists(DB_PATH):
    print("❌ Database file not found. Creating folder if necessary.", flush=True)
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

if not os.path.exists(AWS_PATH):
    print(f"❌ AWS IoT folder not found: {AWS_PATH}", flush=True)
else:
    print("List AWS_PATH:", os.listdir(AWS_PATH), flush=True)

# ---------------- AWS CERT PATHS ----------------
CA_PATH   = os.path.join(AWS_PATH, "AmazonRootCA1.pem")
CERT_PATH = os.path.join(AWS_PATH, "certificate.pem.crt")
KEY_PATH  = os.path.join(AWS_PATH, "private.pem.key")

for name, path in {"CA": CA_PATH, "CERT": CERT_PATH, "KEY": KEY_PATH}.items():
    print(f"{name} exists: {os.path.exists(path)} -> {path}", flush=True)

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
    print(f"Data published, MID={mid}")

# ---------------- MQTT CONNECT ----------------
def connect_mqtt():
    print("Connecting to AWS IoT...", flush=True)
    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311, transport="tcp")
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

# ---------------- WAIT FOR MQTT CONNECTION ----------------
mqtt_client = None
while mqtt_client is None:
    try:
        mqtt_client = connect_mqtt()
    except Exception as e:
        print("❌ MQTT connect error:", e, flush=True)
        time.sleep(5)

# ---------------- DATABASE SETUP ----------------
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()
print("✅ Database connected", flush=True)

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

    try:
        info = mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)
        info.wait_for_publish()  # Wait until message is delivered

        if info.is_published():
            print(
                f"➡️ Uploaded | id={row['id']} | "
                f"BP={row['bp_pressure']} bar | FP={row['fp_pressure']} bar | "
                f"CR={row['cr_pressure']} bar | BC={row['bc_pressure']} bar | "
                f"created_at={row['created_at']}"
            )
            return True
        else:
            print(f"❌ Publish failed for id={row['id']}")
            return False

    except Exception as e:
        print(f"❌ Exception during publish: {e}", flush=True)
        return False

# ---------------- MAIN LOOP ----------------
print("\nSystem started... Uploading unuploaded rows every 5 seconds\n", flush=True)

while True:
    try:
        cursor.execute("SELECT * FROM brake_pressure_log WHERE uploaded = 0 ORDER BY created_at ASC")
        rows = cursor.fetchall()

        if not rows:
            print("No pending rows to upload. Waiting...", flush=True)
            time.sleep(5)
            continue

        for row in rows:
            success = upload_to_aws(row)
            if success:
                cursor.execute("UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?", (row["id"],))
                conn.commit()
                print(f"✅ Marked uploaded | id={row['id']}", flush=True)
            else:
                print("❌ Upload failed, will retry later for this row.", flush=True)
                time.sleep(2)  # Retry next loop

        time.sleep(5)

    except KeyboardInterrupt:
        print("Exiting gracefully...", flush=True)
        break
    except Exception as e:
        print(f"❌ Unexpected error: {e}", flush=True)
        time.sleep(5)
