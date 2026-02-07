import os
import ssl
import json
import time
import signal
import sqlite3
import paho.mqtt.client as mqtt

# ===================== CONFIG =====================

BASE_PATH = "/home/pi_123/data/src/pressure_project"
DB_PATH = f"{BASE_PATH}/db/project.db"
RASPI_PATH = f"{BASE_PATH}/raspi"

CA_FILE = f"{RASPI_PATH}/AmazonRootCA1 (4).pem"
CERT_FILE = f"{RASPI_PATH}/3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-certificate.pem.crt"
KEY_FILE = f"{RASPI_PATH}/3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-private.pem.key"

AWS_ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
CLIENT_ID = "Raspberry_pi"
TOPIC = "brake/pressure"

PUBLISH_INTERVAL = 2  # seconds
running = True

# ===================== SHUTDOWN =====================

def graceful_exit(sig, frame):
    global running
    print("\n🛑 Graceful shutdown")
    running = False

signal.signal(signal.SIGINT, graceful_exit)
signal.signal(signal.SIGTERM, graceful_exit)

# ===================== DEBUG =====================

print("=== DEBUG START ===")
print("PWD:", os.getcwd())
print("DB exists:", os.path.exists(DB_PATH))
print("CA exists:", os.path.exists(CA_FILE))
print("CERT exists:", os.path.exists(CERT_FILE))
print("KEY exists:", os.path.exists(KEY_FILE))
print("=== DEBUG END ===")

# ===================== MQTT CALLBACKS =====================

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core")
    else:
        print(f"❌ MQTT connect failed (RC={rc})")

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("⚠ MQTT disconnected unexpectedly")

# ===================== MQTT CLIENT =====================

client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
client.on_connect = on_connect
client.on_disconnect = on_disconnect

client.tls_set(
    ca_certs=CA_FILE,
    certfile=CERT_FILE,
    keyfile=KEY_FILE,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

client.connect(AWS_ENDPOINT, 8883, 60)
client.loop_start()

# ===================== DATABASE =====================

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# ===================== MAIN LOOP =====================

try:
    while running:
        cursor.execute("""
            SELECT id, bp, fp, cr, bc, created_at
            FROM pressure_data
            WHERE uploaded = 0
            ORDER BY id ASC
            LIMIT 1
        """)
        row = cursor.fetchone()

        if not row:
            time.sleep(PUBLISH_INTERVAL)
            continue

        record_id, bp, fp, cr, bc, timestamp = row

        payload = {
            "id": record_id,
            "BP": bp,
            "FP": fp,
            "CR": cr,
            "BC": bc,
            "timestamp": timestamp
        }

        # ---- LOCAL TERMINAL PRINT ----
        print(
            f"📤 Local data -> id={record_id} | "
            f"BP:{bp} | FP:{fp} | CR:{cr} | BC:{bc} | "
            f"timestamp:{timestamp}"
        )

        result = client.publish(TOPIC, json.dumps(payload), qos=1)

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            cursor.execute(
                "UPDATE pressure_data SET uploaded = 1 WHERE id = ?",
                (record_id,)
            )
            conn.commit()

            print(
                f'✅ Uploaded & marked | id={record_id} timestamp="{timestamp}"'
            )
            print(
                "AWS IoT sent:\n"
                f"id={record_id} | BP:{bp} | FP:{fp} | "
                f"CR:{cr} | BC:{bc} | timestamp:{timestamp}\n"
            )

        time.sleep(PUBLISH_INTERVAL)

finally:
    client.loop_stop()
    client.disconnect()
    conn.close()
