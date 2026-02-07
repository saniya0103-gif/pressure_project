import sqlite3
import time
import json
import ssl
import os
import sys
import signal
import paho.mqtt.client as mqtt

# ================= PATH SETUP =================
BASE_PATH = "/app" if os.path.exists("/app") else os.path.dirname(os.path.abspath(__file__))
RASPI_PATH = os.path.join(BASE_PATH, "raspi")
DB_PATH = os.path.join(BASE_PATH, "db", "project.db")

CA_PATH = os.path.join(RASPI_PATH, "AmazonRootCA1 (4).pem")
CERT_PATH = os.path.join(RASPI_PATH, "3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-certificate.pem.crt")
KEY_PATH = os.path.join(RASPI_PATH, "3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-private.pem.key")

print("=== DEBUG START ===", flush=True)
print("PWD:", BASE_PATH, flush=True)
print("DB exists:", os.path.exists(DB_PATH))
print("CA exists:", os.path.exists(CA_PATH))
print("CERT exists:", os.path.exists(CERT_PATH))
print("KEY exists:", os.path.exists(KEY_PATH))
print("=== DEBUG END ===", flush=True)

# ================= MQTT CONFIG =================
ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
PORT = 8883
CLIENT_ID = "Raspberry_pi"
TOPIC = "brake/pressure"

mqtt_client = None
connected = False

# ================= CALLBACKS =================
def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        connected = True
        print("✅ Connected to AWS IoT Core", flush=True)
    else:
        print(f"❌ MQTT connect failed, RC={rc}", flush=True)

def on_disconnect(client, userdata, rc):
    global connected
    connected = False
    print(f"⚠ MQTT disconnected, RC={rc}", flush=True)

# ================= MQTT CONNECT =================
def connect_mqtt():
    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect

    client.tls_set(
        ca_certs=CA_PATH,
        certfile=CERT_PATH,
        keyfile=KEY_PATH,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )

    client.connect(ENDPOINT, PORT, keepalive=60)
    client.loop_start()
    return client

# ================= CONNECT RETRY =================
while mqtt_client is None or not connected:
    try:
        print("🔌 Connecting to AWS IoT...", flush=True)
        mqtt_client = connect_mqtt()
        time.sleep(3)
    except Exception as e:
        print("❌ MQTT connection error:", e, flush=True)
        time.sleep(5)

# ================= DATABASE =================
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ================= UPLOAD FUNCTION =================
def upload_to_aws(row):
    if not connected:
        return False

    payload = {
        "created_at": row["created_at"],
        "bp_pressure": row["bp_pressure"],
        "fp_pressure": row["fp_pressure"],
        "cr_pressure": row["cr_pressure"],
        "bc_pressure": row["bc_pressure"]
    }

    result = mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)
    result.wait_for_publish()

    return result.rc == mqtt.MQTT_ERR_SUCCESS

# ================= MAIN LOOP =================
try:
    while True:
        cursor.execute("""
            SELECT * FROM brake_pressure_log
            WHERE uploaded = 0
            ORDER BY created_at ASC
        """)
        rows = cursor.fetchall()

        if not rows:
            time.sleep(5)
            continue

        for row in rows:
            if upload_to_aws(row):
                cursor.execute(
                    "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                    (row["id"],)
                )
                conn.commit()
                print(f"✅ Uploaded & marked | id={row['id']}", flush=True)
            else:
                print("⚠ Upload failed, retrying later", flush=True)
                break

            time.sleep(2)

except KeyboardInterrupt:
    pass

# ================= SHUTDOWN =================
def shutdown(sig, frame):
    print("🛑 Graceful shutdown", flush=True)
    try:
        mqtt_client.loop_stop()
        mqtt_client.disconnect()
    except:
        pass
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)
