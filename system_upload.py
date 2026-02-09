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

# Root CA only is needed for WebSockets
CA_PATH = os.path.join(RASPI_PATH, "AmazonRootCA1 (4).pem")

ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
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
print("=== DEBUG END ===")

for f in [DB_PATH, CA_PATH]:
    if not os.path.exists(f):
        raise FileNotFoundError(f"❌ Missing file: {f}")

# ================= MQTT CALLBACKS =================
def on_connect(client, userdata, flags, rc, properties=None):
    global CONNECTED
    if rc == 0:
        CONNECTED = True
        print("✅ Connected to AWS IoT Core")
    else:
        print("❌ MQTT connection failed, RC:", rc)

def on_disconnect(client, userdata, rc, properties=None):
    global CONNECTED
    CONNECTED = False
    print("⚠️ MQTT disconnected, reason:", rc)

# ================= MQTT CLIENT =================
CLIENT_ID = f"Raspberry_pi_{int(time.time())}"  # Unique ID

client = mqtt.Client(
    client_id=CLIENT_ID,
    transport="websockets"  # ✅ Use WebSockets
)

client.on_connect = on_connect
client.on_disconnect = on_disconnect

client.tls_set(
    ca_certs=CA_PATH,
    tls_version=ssl.PROTOCOL_TLSv1_2
)
client.tls_insecure_set(False)
client.reconnect_delay_set(min_delay=2, max_delay=60)

# ================= CONNECT =================
try:
    client.connect(ENDPOINT, 443, keepalive=60)  # ✅ Port 443 for WebSockets
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
            "timestamp": str(created_at)
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
                f'✅ Uploaded | id={id_} BP={bp} FP={fp} CR={cr} BC={bc} timestamp="{created_at}"'
            )
            print(
                f'📤 AWS IoT Sent {{ id={id_} BP={bp} FP={fp} CR={cr} BC={bc} timestamp="{created_at}" }}'
            )
        else:
            print("❌ Publish failed, rc =", result.rc)

        time.sleep(1)

finally:
    print("🔻 Shutting down cleanly...")
    try:
        client.loop_stop()
        client.disconnect()
    except Exception:
        pass
    conn.close()
    print("✅ Shutdown complete")
