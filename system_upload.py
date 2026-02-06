import sqlite3
import time
import json
import ssl
import os
import gc
import threading
import glob
from paho.mqtt.client import Client, CallbackAPIVersion, MQTTv311

# ---------------- BASE PATH ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------- PATHS ----------------
AWS_PATH = os.path.join(BASE_DIR, "raspi")       # Certificates folder
DB_PATH  = os.path.join(BASE_DIR, "db", "project.db")  # Database file

# ---------------- AUTO-DETECT CERTIFICATES ----------------
# Use AmazonRootCA1.pem for AWS IoT TLS verification
CA_PATH = os.path.join(AWS_PATH, "AmazonRootCA1.pem")
if not os.path.exists(CA_PATH):
    raise FileNotFoundError("AmazonRootCA1.pem not found in raspi folder")

# Auto-detect device certificate and private key
CERTS = glob.glob(os.path.join(AWS_PATH, "*-certificate.pem.crt"))
KEYS = glob.glob(os.path.join(AWS_PATH, "*-private.pem.key"))

if not CERTS or not KEYS:
    raise FileNotFoundError("Device certificate or private key not found in raspi folder")

CERT_PATH = CERTS[0]
KEY_PATH  = KEYS[0]

# Verify database exists
if not os.path.exists(DB_PATH):
    raise FileNotFoundError(f"Database not found: {DB_PATH}")

print("✅ All certificate files and database found", flush=True)

# ---------------- MQTT CONFIG ----------------
ENDPOINT  = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
PORT      = 8883
CLIENT_ID = "Raspberry_pi"
TOPIC     = "brake/pressure"

# ---------------- DATABASE CONNECTION ----------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ---------------- MQTT FLAGS ----------------
connected_flag = False

# ---------------- MQTT CALLBACKS ----------------
def on_connect(client, userdata, flags, rc, properties=None):
    global connected_flag
    if rc == 0:
        connected_flag = True
        print("✅ Connected to AWS IoT Core", flush=True)
    else:
        connected_flag = False
        print(f"❌ MQTT connect failed: {rc}", flush=True)

def on_disconnect(client, userdata, rc):
    global connected_flag
    connected_flag = False
    if rc != 0:
        print("⚠️ Disconnected unexpectedly. Will reconnect automatically...", flush=True)

# ---------------- MQTT CONNECT ----------------
def start_mqtt():
    client = Client(
        client_id=CLIENT_ID,
        protocol=MQTTv311,
        callback_api_version=CallbackAPIVersion.VERSION1
    )

    # ✅ TLS setup with proper CA for AWS IoT Core
    client.tls_set(
        ca_certs=CA_PATH,       # AmazonRootCA1.pem
        certfile=CERT_PATH,
        keyfile=KEY_PATH,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )

    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    # Non-blocking MQTT loop
    client.loop_start()

    # Retry connect until successful
    while True:
        try:
            client.connect(ENDPOINT, PORT, keepalive=60)
            break
        except ssl.SSLError as ssl_err:
            print(f"❌ SSL error: {ssl_err}", flush=True)
            print("🔹 Check your CA certificate (AmazonRootCA1.pem)", flush=True)
            time.sleep(5)
        except Exception as e:
            print(f"❌ MQTT connect error: {e}", flush=True)
            time.sleep(5)

    return client

mqtt_client = start_mqtt()

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

    for _ in range(retries):
        if not connected_flag:
            time.sleep(0.5)
            continue

        result = mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)
        mqtt_client.loop(0.05)  # process network events

        if result.rc == mqtt_client.MQTT_ERR_SUCCESS:
            print(
                f"➡️ Uploaded | id={row['id']} | "
                f"BP={row['bp_pressure']} | FP={row['fp_pressure']} | "
                f"CR={row['cr_pressure']} | BC={row['bc_pressure']} | "
                f"time={row['created_at']}",
                flush=True
            )
            gc.collect()
            return True

        time.sleep(0.5)

    return False

# ---------------- DATABASE UPLOAD LOOP WITH BATCH FETCH ----------------
BATCH_SIZE = 5  # smaller batch for memory efficiency

def upload_loop():
    try:
        while True:
            cursor.execute("""
                SELECT * FROM brake_pressure_log
                WHERE uploaded = 0
                ORDER BY created_at ASC
                LIMIT ?
            """, (BATCH_SIZE,))
            rows = cursor.fetchall()

            if not rows:
                time.sleep(1)
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
                    print(f"❌ Could not upload id={row['id']}. Will retry later.", flush=True)

    except KeyboardInterrupt:
        pass
    finally:
        conn.close()

# ---------------- START UPLOAD THREAD ----------------
thread = threading.Thread(target=upload_loop, daemon=True)
thread.start()

# ---------------- KEEP SCRIPT RUNNING ----------------
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    print("\n Interrupted by user. Exiting...")
finally:
    if mqtt_client:
        mqtt_client.disconnect()
    print("✅ Cleanup done. Exiting program.")
