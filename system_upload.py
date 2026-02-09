import os
import json
import time
import ssl
import signal
import sys
import sqlite3
import paho.mqtt.client as mqtt

# ================= PATH CONFIG =================
BASE_PATH = "/home/pi_123/data/src/pressure_project"
DB_PATH = f"{BASE_PATH}/db/project.db"
RASPI_PATH = f"{BASE_PATH}/raspi"

CA_PATH   = f"{RASPI_PATH}/AmazonRootCA1 (4).pem"
CERT_PATH = f"{RASPI_PATH}/3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-certificate.pem.crt"
KEY_PATH  = f"{RASPI_PATH}/3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-private.pem.key"

ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
CLIENT_ID = "Raspberry_pi"
TOPIC = "brake/pressure"

RUNNING = True
CONNECTED = False

# ================= SIGNAL HANDLING =================
def shutdown_handler(signum, frame):
    global RUNNING
    print("🛑 Shutdown signal received")
    RUNNING = False

signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)

# ================= FILE CHECK =================
print("=== DEBUG START ===")
print("DB exists:", os.path.exists(DB_PATH))
print("CA exists:", os.path.exists(CA_PATH))
print("CERT exists:", os.path.exists(CERT_PATH))
print("KEY exists:", os.path.exists(KEY_PATH))
print("=== DEBUG END ===")

for f in [DB_PATH, CA_PATH, CERT_PATH, KEY_PATH]:
    if not os.path.exists(f):
        raise FileNotFoundError(f"❌ Missing file: {f}")

# ================= MQTT CALLBACKS =================
def on_connect(client, userdata, flags, rc):
    global CONNECTED
    if rc == 0:
        CONNECTED = True
        print("✅ Connected to AWS IoT Core")
    else:
        print("❌ MQTT connection failed, RC:", rc)

def on_disconnect(client, userdata, rc):
    global CONNECTED
    CONNECTED = False
    print("⚠️ MQTT disconnected (rc =", rc, ")")

# ================= MQTT CLIENT =================
client = mqtt.Client(
    client_id=CLIENT_ID,
    protocol=mqtt.MQTTv311,
    clean_session=True
)

client.on_connect = on_connect
client.on_disconnect = on_disconnect

client.tls_set(
    ca_certs=CA_PATH,
    certfile=CERT_PATH,
    keyfile=KEY_PATH,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

client.tls_insecure_set(False)
client.reconnect_delay_set(min_delay=2, max_delay=60)

# ================= CONNECT =================
try:
    client.connect(ENDPOINT, 8883, keepalive=60)
except Exception as e:
    print("❌ Initial MQTT connect failed:", e)
    sys.exit(1)

client.loop_start()

# ================= DATABASE =================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

# ================= MAIN LOOP =================
try:
    while RUNNING:
        if not CONNECTED:
            time.sleep(2)
            continue

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

        result = client.publish(TOPIC, json.dumps(payload), qos=1)
        result.wait_for_publish()

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            cursor.execute(
                "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                (id_,)
            )
            conn.commit()

            print(
                f'✅ Uploaded | id={id_} timestamp="{created_at}" '
                f'BP={bp} FP={fp} CR={cr} BC={bc}'
            )
            print(
                f'📤 AWS IoT Sent {{ timestamp="{created_at}", id={id_}, '
                f'bp={bp}, fp={fp}, cr={cr}, bc={bc} }}'
            )
        else:
            print("❌ Publish failed, rc =", result.rc)

        time.sleep(1)

finally:
    print("🔻 Shutting down cleanly...")
    client.loop_stop()
    client.disconnect()
    conn.close()
    print("✅ Shutdown complete")
