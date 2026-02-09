import os
import json
import time
import ssl
import signal
import sys
import sqlite3
import socket
import paho.mqtt.client as mqtt

# ================= PATH CONFIG =================
BASE_PATH = os.getenv("APP_BASE_PATH", "/home/pi_123/data/src/pressure_project")
DB_PATH = f"{BASE_PATH}/db/project.db"
RASPI_PATH = f"{BASE_PATH}/raspi"

CA_FILE = f"{RASPI_PATH}/AmazonRootCA1 (4).pem"
CERT_FILE = f"{RASPI_PATH}/3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-certificate.pem.crt"
KEY_FILE = f"{RASPI_PATH}/3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-private.pem.key"

ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
CLIENT_ID = "Raspberry_pi"
TOPIC = "brake/pressure"

RUNNING = True

# ================= SIGNAL HANDLING =================
def shutdown_handler(signum, frame):
    global RUNNING
    print("🛑 Shutdown signal received")
    RUNNING = False

signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)

# ================= INTERNET WAIT =================
def wait_for_internet():
    while True:
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=5)
            print("🌐 Internet ready")
            return
        except OSError:
            print("⏳ Waiting for internet...")
            time.sleep(5)

# ================= DEBUG =================
print("=== DEBUG START ===")
print("BASE_PATH:", BASE_PATH)
print("DB exists:", os.path.exists(DB_PATH))
print("CA exists:", os.path.exists(CA_FILE))
print("CERT exists:", os.path.exists(CERT_FILE))
print("KEY exists:", os.path.exists(KEY_FILE))
print("=== DEBUG END ===")

# ================= MQTT CALLBACKS =================
def on_connect(client, userdata, flags, reason_code, properties=None):
    if reason_code == 0:
        print("✅ Connected to AWS IoT Core")
    else:
        print("❌ MQTT connect failed, RC:", reason_code)

def on_disconnect(client, userdata, reason_code, properties=None):
    print("⚠️ MQTT disconnected, RC:", reason_code)

# ================= MQTT CLIENT =================
client = mqtt.Client(
    client_id=CLIENT_ID,
    protocol=mqtt.MQTTv311,
    callback_api_version=mqtt.CallbackAPIVersion.VERSION2
)

client.on_connect = on_connect
client.on_disconnect = on_disconnect

client.tls_set(
    ca_certs=CA_FILE,
    certfile=CERT_FILE,
    keyfile=KEY_FILE,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

client.tls_insecure_set(False)
client.reconnect_delay_set(min_delay=5, max_delay=60)

# ================= CONNECT =================
wait_for_internet()

while True:
    try:
        print("🔌 Connecting to AWS IoT...")
        client.connect(ENDPOINT, 8883, keepalive=60)
        break
    except Exception as e:
        print("AWS IoT connect failed:", e)
        time.sleep(10)

client.loop_start()

# ================= DATABASE =================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# ================= MAIN LOOP =================
try:
    while RUNNING:
        cursor.execute("""
            SELECT id, bp_pressure, fp_pressure, cr_pressure, bc_pressure, created_at
            FROM brake_pressure_log
            WHERE uploaded = 0
            ORDER BY id ASC
            LIMIT 1
        """)
        row = cursor.fetchone()

        if not row:
            time.sleep(2)
            continue

        id_, bp, fp, cr, bc, created_at = row

        payload = {
            "id": id_,
            "bp": bp,
            "fp": fp,
            "cr": cr,
            "bc": bc,
            "timestamp": created_at
        }

        try:
            info = client.publish(TOPIC, json.dumps(payload), qos=1)
            info.wait_for_publish()

            if info.rc == mqtt.MQTT_ERR_SUCCESS:
                cursor.execute(
                    "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                    (id_,)
                )
                conn.commit()
                print(f"✅ Uploaded | id={id_} time={created_at}")
            else:
                print("❌ Publish failed, RC:", info.rc)

        except Exception as e:
            print("❌ MQTT publish error:", e)

        time.sleep(1)

finally:
    print("🔻 CLEANING UP RESOURCES...")
    client.loop_stop()
    client.disconnect()
    conn.close()
    print("✅ Shutdown complete")
    sys.exit(0)
