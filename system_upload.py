import os
import json
import time
import ssl
import signal
import sys
import sqlite3
import paho.mqtt.client as mqtt

# ================= GLOBAL FLAG =================
RUNNING = True

# ================= PATH CONFIG =================
BASE_PATH = os.getenv("APP_BASE_PATH", "/home/pi_123/data/src/pressure_project")

DB_PATH = f"{BASE_PATH}/db/project.db"
CERT_PATH = f"{BASE_PATH}/raspi"

CA_FILE   = f"{CERT_PATH}/AmazonRootCA1 (4).pem"
CERT_FILE = f"{CERT_PATH}/3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-certificate.pem.crt"
KEY_FILE  = f"{CERT_PATH}/3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-private.pem.key"

ENDPOINT  = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
CLIENT_ID = "Raspberry_pi"
TOPIC     = "brake/pressure"

# ================= SIGNAL HANDLER =================
def shutdown_handler(signum, frame):
    global RUNNING
    print("\n🛑 Shutdown signal received")
    RUNNING = False

signal.signal(signal.SIGTERM, shutdown_handler)
signal.signal(signal.SIGINT, shutdown_handler)

# ================= DEBUG PRINT =================
print("\n========== STARTUP DEBUG ==========")
print("📁 BASE_PATH       :", BASE_PATH)
print("📄 DB_PATH         :", DB_PATH, "| exists:", os.path.exists(DB_PATH))
print("🔐 CA_FILE         :", CA_FILE, "| exists:", os.path.exists(CA_FILE))
print("🔐 CERT_FILE       :", CERT_FILE, "| exists:", os.path.exists(CERT_FILE))
print("🔐 KEY_FILE        :", KEY_FILE, "| exists:", os.path.exists(KEY_FILE))
print("🌐 AWS ENDPOINT    :", ENDPOINT)
print("📡 MQTT TOPIC      :", TOPIC)
print("==================================\n")

# ================= MQTT CALLBACKS =================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT CONNECTED to AWS IoT Core")
    else:
        print("❌ MQTT CONNECTION FAILED | RC =", rc)

def on_disconnect(client, userdata, rc):
    print("⚠️ MQTT DISCONNECTED | RC =", rc)

# ================= MQTT CLIENT =================
client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.enable_logger()  # very important for docker logs

client.tls_set(
    ca_certs=CA_FILE,
    certfile=CERT_FILE,
    keyfile=KEY_FILE,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

client.reconnect_delay_set(min_delay=1, max_delay=30)

print("🔄 Connecting to AWS IoT...")
client.connect(ENDPOINT, 8883)
client.loop_start()

# ================= DATABASE =================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

print("📦 SQLite database connected")

# ================= MAIN LOOP =================
try:
    while RUNNING:
        cursor.execute("""
            SELECT id,
                   bp_pressure,
                   fp_pressure,
                   cr_pressure,
                   bc_pressure,
                   created_at
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

        print(f"\n📤 Publishing ID {id_} to AWS...")
        info = client.publish(TOPIC, json.dumps(payload), qos=1)
        info.wait_for_publish()

        if info.rc == mqtt.MQTT_ERR_SUCCESS:
            cursor.execute(
                "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                (id_,)
            )
            conn.commit()

            print(f'✅ Uploaded | id={id_} | timestamp="{created_at}"')
            print(
                f'☁️ AWS sent data:\n'
                f'   {{ id:{id_} | BP:{bp} | FP:{fp} | CR:{cr} | BC:{bc} | timestamp:{created_at} }}'
            )
        else:
            print("❌ Publish failed | RC =", info.rc)

        time.sleep(1)

finally:
    print("\n🔻 CLEANING UP RESOURCES...")
    try:
        client.loop_stop()
        client.disconnect()
    except:
        pass

    try:
        conn.close()
    except:
        pass

    print("✅ Shutdown complete")
    sys.exit(0)
