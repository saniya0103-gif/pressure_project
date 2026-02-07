import os
import json
import time
import ssl
import signal
import sys
import sqlite3
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

# ================= DEBUG CHECKS =================
print("=== DEBUG START ===")
print("BASE_PATH:", BASE_PATH)
print("DB exists:", os.path.exists(DB_PATH))
print("CA exists:", os.path.exists(CA_FILE))
print("CERT exists:", os.path.exists(CERT_FILE))
print("KEY exists:", os.path.exists(KEY_FILE))
print("=== DEBUG END ===")

# ================= MQTT SETUP =================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core")
    else:
        print("❌ MQTT connect failed, RC:", rc)

def on_disconnect(client, userdata, rc):
    print(f"⚠️ MQTT disconnected, RC: {rc}")

client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
client.on_connect = on_connect
client.on_disconnect = on_disconnect

client.tls_set(
    ca_certs=CA_FILE,
    certfile=CERT_FILE,
    keyfile=KEY_FILE,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

# Slow reconnect to avoid AWS throttling
client.reconnect_delay_set(min_delay=2, max_delay=60)

# Connect and start loop
try:
    client.connect(ENDPOINT, 8883, keepalive=60)
except Exception as e:
    print("❌ MQTT initial connect failed:", e)
    sys.exit(1)

client.loop_start()

# ================= DATABASE =================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# ================= PUBLISH FUNCTION WITH RETRY =================
def publish_payload(payload):
    for attempt in range(3):  # retry up to 3 times
        try:
            info = client.publish(TOPIC, json.dumps(payload), qos=1)
            info.wait_for_publish()
            if info.rc == mqtt.MQTT_ERR_SUCCESS:
                return True
        except Exception as e:
            print(f"❌ MQTT publish attempt {attempt+1} failed:", e)
        time.sleep(2)
    return False

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
            # No data to send, sleep longer to save memory
            time.sleep(5)
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

        if publish_payload(payload):
            cursor.execute("UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?", (id_,))
            conn.commit()
            print(f"✅ Uploaded | id={id_} timestamp=\"{created_at}\"")
            print(f"📤 AWS IoT sent: {{ id:{id_} | BP:{bp} | FP:{fp} | CR:{cr} | BC:{bc} | timestamp:{created_at} }}")
        else:
            print(f"❌ Failed to publish id={id_}, will retry later")

        # Sleep 2 sec to reduce CPU/memory pressure
        time.sleep(2)

except KeyboardInterrupt:
    print("🛑 Graceful shutdown (KeyboardInterrupt)")

finally:
    print("🔻 CLEANING UP RESOURCES...")
    client.loop_stop()
    client.disconnect()
    conn.close()
    print("✅ Shutdown complete")
    sys.exit(0)
