import sqlite3
import time
import json
import ssl
import os
import gc
import threading
import socket  # Added for unique Client ID
import paho.mqtt.client as mqtt
from paho.mqtt.client import CallbackAPIVersion # FIX: Deprecation

# ---------------- BASE PATH ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------- PATHS ----------------
AWS_PATH = os.path.join(BASE_DIR, "raspi")
DB_PATH  = os.path.join(BASE_DIR, "db", "project.db")

# ---------------- CERTIFICATES ----------------
CA_PATH   = os.path.join(AWS_PATH, "AmazonRootCA1.pem")
CERT_PATH = os.path.join(AWS_PATH, "0a0f7d38323fdef876a81f1a8d6671502e80d50d6e2fdc753a68baa51cfcf5ef-certificate.pem.crt")
KEY_PATH  = os.path.join(AWS_PATH, "0a0f7d38323fdef876a81f1a8d6671502e80d50d6e2fdc753a68baa51cfcf5ef-private.pem.key")

# ---------------- VERIFY FILES ----------------
for name, path in {"CA": CA_PATH, "CERT": CERT_PATH, "KEY": KEY_PATH, "DB": DB_PATH}.items():
    if not os.path.exists(path):
        raise FileNotFoundError(f"{name} not found: {path}")

print("✅ All certificate files and database found", flush=True)

# ---------------- MQTT CONFIG ----------------
ENDPOINT  = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
PORT      = 8883
# FIX: Unique Client ID prevents "Disconnected unexpectedly"
CLIENT_ID = f"Raspberry_pi_{socket.gethostname()}" 
TOPIC     = "brake/pressure"

# ---------------- DATABASE CONNECTION ----------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=20)
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

def on_disconnect(client, userdata, rc, properties=None):
    global connected_flag
    connected_flag = False
    if rc != 0:
        print("⚠️ Disconnected unexpectedly. Reconnecting...", flush=True)

# ---------------- MQTT CONNECT ----------------
def start_mqtt():
    # FIX: Added CallbackAPIVersion.VERSION1
    client = mqtt.Client(CallbackAPIVersion.VERSION1, client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
    client.tls_set(
        ca_certs=CA_PATH,
        certfile=CERT_PATH,
        keyfile=KEY_PATH,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    while True:
        try:
            client.connect(ENDPOINT, PORT, keepalive=60)
            client.loop_start() # FIX: Use loop_start for background threading
            break
        except Exception as e:
            print(f"❌ MQTT connect error: {e}", flush=True)
            time.sleep(5)
    return client

mqtt_client = start_mqtt()

# ---------------- UPLOAD FUNCTION ----------------
def upload_to_aws(row, retries=3):
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
            time.sleep(1)
            continue

        result = mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)
        
        # FIX: result.rc uses the mqtt module constant MQTT_ERR_SUCCESS
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"➡️ Uploaded | id={row['id']}", flush=True)
            return True
        time.sleep(0.5)
    return False

# ---------------- DATABASE UPLOAD LOOP ----------------
BATCH_SIZE = 10 

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
                time.sleep(2)
                continue

            for row in rows:
                if upload_to_aws(row):
                    cursor.execute("UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?", (row["id"],))
                    conn.commit()
                    gc.collect()
                else:
                    print(f"❌ Failed id={row['id']}", flush=True)
            
            time.sleep(0.1)
    except Exception as e:
        print(f"Critial Error in thread: {e}")

# ---------------- MAIN ----------------
if __name__ == "__main__":
    thread = threading.Thread(target=upload_loop, daemon=True)
    thread.start()

    try:
        while True:
            # Check if thread is still alive
            if not thread.is_alive():
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user. Exiting...")
    finally:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
        conn.close()
        print("✅ Cleanup done. Exiting program.")
