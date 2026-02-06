import sqlite3
import time
import json
import ssl
import os
import gc
import paho.mqtt.client as mqtt

# ---------------- BASE PATH ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------- PATHS ----------------
AWS_PATH = os.path.join(BASE_DIR, "raspi")       # Certificates folder
DB_PATH  = os.path.join(BASE_DIR, "db", "project.db")  # Database file

# ---------------- CERTIFICATES ----------------
CA_PATH   = os.path.join(AWS_PATH, "AmazonRootCA1.pem")
CERT_PATH = os.path.join(AWS_PATH, "0a0f7d38323fdef876a81f1a8d6671502e80d50d6e2fdc753a68baa51cfcf5ef-certificate.pem.crt")
KEY_PATH  = os.path.join(AWS_PATH, "0a0f7d38323fdef876a81f1a8d6671502e80d50d6e2fdc753a68baa51cfcf5ef-private.pem.key")

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
CLIENT_ID = "Raspberry_pi"
TOPIC     = "brake/pressure"

# ---------------- MQTT FLAGS ----------------
connected_flag = False

# ---------------- MQTT CALLBACKS ----------------
def on_connect(client, userdata, flags, rc):
    global connected_flag
    if rc == 0:
        print("✅ Connected to AWS IoT Core", flush=True)
        connected_flag = True
    else:
        print("❌ MQTT connect failed:", rc, flush=True)
        connected_flag = False

def on_publish(client, userdata, mid):
    print("📤 Message published", flush=True)

# ---------------- MQTT CONNECT ----------------
def connect_mqtt():
    print("🔄 Connecting to AWS IoT...", flush=True)

    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_publish = on_publish

    client.tls_set(
        ca_certs=CA_PATH,
        certfile=CERT_PATH,
        keyfile=KEY_PATH,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )

    # Retry until fully connected
    while True:
        try:
            client.connect(ENDPOINT, PORT, keepalive=60)
            client.loop_start()  # Start network loop once
            break
        except Exception as e:
            print("❌ MQTT connect error:", e, flush=True)
            time.sleep(5)

    # Wait until connected_flag is True
    while not connected_flag:
        print("⏳ Waiting for MQTT connection...", flush=True)
        time.sleep(2)

    return client

mqtt_client = connect_mqtt()

# ---------------- DATABASE CONNECTION ----------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ---------------- UPLOAD FUNCTION ----------------
def upload_to_aws(row, retries=5):
    payload = {
        "id": row["id"],
        "timestamp": row["created_at"],
        "bp": row["bp_pressure"],
        "fp": row["fp_pressure"],
        "cr": row["cr_pressure"],
        "bc": row["bc_pressure"]
    }

    for attempt in range(retries):
        if not connected_flag:
            print("⚠️ MQTT not connected. Waiting...", flush=True)
            time.sleep(2)
            continue

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
            print(f"❌ Publish failed attempt {attempt+1}/{retries}: {result.rc}", flush=True)
            time.sleep(2)

    return False

# ---------------- MAIN LOOP ----------------
try:
    while True:
        cursor.execute("""
            SELECT * FROM brake_pressure_log
            WHERE uploaded = 0
            ORDER BY created_at ASC
        """)
        rows = cursor.fetchall()

        if not rows:
            print("⏳ No pending rows. Waiting...", flush=True)
            time.sleep(10)
            continue

        for row in rows:
            success = upload_to_aws(row)
            if success:
                cursor.execute(
                    "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                    (row["id"],)
                )
                conn.commit()
                print(f"✅ Marked uploaded | id={row['id']}", flush=True)
            else:
                print(f"❌ Skipped id={row['id']} due to publish error", flush=True)
                time.sleep(5)

except KeyboardInterrupt:
    print("\n🛑 Interrupted by user. Exiting...")

finally:
    conn.close()
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    print("✅ Cleanup done. Exiting program.")
