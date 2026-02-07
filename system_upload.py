import sqlite3
import time
import json
import ssl
import os
import paho.mqtt.client as mqtt
import signal
import sys

# ---------------- BASE PATH ----------------
BASE_PATH = "/app" if os.path.exists("/app") else os.path.dirname(os.path.abspath(__file__))
RASPI_PATH = os.path.join(BASE_PATH, "raspi")
DB_PATH = os.path.join(BASE_PATH, "db", "project.db")

# ---------------- DEBUG ----------------
print("=== DEBUG START ===", flush=True)
print("PWD:", BASE_PATH, flush=True)

if not os.path.exists(RASPI_PATH):
    print("❌ RASPI folder not found:", RASPI_PATH)
    sys.exit(1)

# ---------------- CERTIFICATE DETECTION ----------------
CERT_PATH = next((os.path.join(RASPI_PATH, f) for f in os.listdir(RASPI_PATH) if f.endswith("-certificate.pem.crt")), None)
KEY_PATH = next((os.path.join(RASPI_PATH, f) for f in os.listdir(RASPI_PATH) if f.endswith("-private.pem.key")), None)
CA_PATH = next((os.path.join(RASPI_PATH, f) for f in os.listdir(RASPI_PATH) if f.startswith("AmazonRootCA") and f.endswith(".pem")), None)

if not all([CERT_PATH, KEY_PATH, CA_PATH]):
    print("❌ Certificate files missing in raspi folder")
    sys.exit(1)

print("DB exists:", os.path.exists(DB_PATH), DB_PATH)
print("CA exists:", os.path.exists(CA_PATH), CA_PATH)
print("CERT exists:", os.path.exists(CERT_PATH), CERT_PATH)
print("KEY exists:", os.path.exists(KEY_PATH), KEY_PATH)
print("=== DEBUG END ===", flush=True)

# ---------------- MQTT CONFIG ----------------
ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
PORT = 8883
CLIENT_ID = "Raspberry"
TOPIC = "brake/pressure"

mqtt_client = None

# ---------------- CALLBACKS ----------------
def on_connect(client, userdata, flags, rc):
    print(f"🔗 MQTT Connected, RC={rc}" if rc == 0 else f"❌ MQTT connect failed, RC={rc}")

def on_publish(client, userdata, mid):
    print("📤 Data published")

# ---------------- GRACEFUL SHUTDOWN ----------------
def shutdown(sig, frame):
    print("🛑 Graceful shutdown")
    if mqtt_client:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    if 'conn' in globals():
        conn.close()
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# ---------------- MQTT CONNECT FUNCTION ----------------
def connect_mqtt(retry_interval=5):
    global mqtt_client
    while mqtt_client is None:
        try:
            print("🔌 Connecting to AWS IoT...")
            client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
            client.on_connect = on_connect
            client.on_publish = on_publish
            client.tls_set(ca_certs=CA_PATH, certfile=CERT_PATH, keyfile=KEY_PATH, tls_version=ssl.PROTOCOL_TLSv1_2)
            client.connect(ENDPOINT, PORT, keepalive=60)
            client.loop_start()
            mqtt_client = client
            print("✅ MQTT connection established")
        except Exception as e:
            print("❌ MQTT connection error:", e)
            time.sleep(retry_interval)

# ---------------- DATABASE SETUP ----------------
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
    try:
        result = mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"➡️ Uploaded | id={row['id']} | BP={row['bp_pressure']} FP={row['fp_pressure']} CR={row['cr_pressure']} BC={row['bc_pressure']}")
            return True
    except Exception as e:
        print("❌ Upload error:", e)
    return False

# ---------------- MAIN LOOP ----------------
def main_loop():
    while True:
        try:
            cursor.execute("SELECT * FROM brake_pressure_log WHERE uploaded=0 ORDER BY created_at ASC")
            rows = cursor.fetchall()
            if not rows:
                print("⏳ No pending rows. Waiting...")
                time.sleep(5)
                continue
            for row in rows:
                if upload_to_aws(row):
                    cursor.execute("UPDATE brake_pressure_log SET uploaded=1 WHERE id=?", (row["id"],))
                    conn.commit()
                else:
                    print("⚠️ Upload failed, retrying next loop")
                    break
                time.sleep(1)
        except Exception as e:
            print("❌ Error in main loop:", e)
            time.sleep(5)

# ---------------- RUN ----------------
if __name__ == "__main__":
    connect_mqtt()
    main_loop()
