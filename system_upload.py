import os
import json
import time
import ssl
import sqlite3
import paho.mqtt.client as mqtt

# ================= PATH CONFIG (FINAL FIX) =================
# Docker will set APP_BASE_PATH=/app
# Local run will use the default path
BASE_PATH = os.getenv(
    "APP_BASE_PATH",
    "/home/pi_123/data/src/pressure_project"
)

DB_PATH = f"{BASE_PATH}/db/project.db"
RASPI_PATH = f"{BASE_PATH}/raspi"

CA_FILE = f"{RASPI_PATH}/AmazonRootCA1 (4).pem"
CERT_FILE = f"{RASPI_PATH}/3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-certificate.pem.crt"
KEY_FILE = f"{RASPI_PATH}/3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-private.pem.key"

ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
CLIENT_ID = "Raspberry_pi"
TOPIC = "brake/pressure"

# ================= DEBUG CHECK =================
print("=== DEBUG START ===")
print("BASE_PATH:", BASE_PATH)
print("DB exists:", os.path.exists(DB_PATH))
print("CA exists:", os.path.exists(CA_FILE))
print("CERT exists:", os.path.exists(CERT_FILE))
print("KEY exists:", os.path.exists(KEY_FILE))
print("=== DEBUG END ===")

# ================= MQTT =================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core")
    else:
        print("❌ MQTT connect failed, RC:", rc)

client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
client.on_connect = on_connect

client.tls_set(
    ca_certs=CA_FILE,
    certfile=CERT_FILE,
    keyfile=KEY_FILE,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

client.connect(ENDPOINT, 8883)
client.loop_start()

# ================= DATABASE =================
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

try:
    while True:
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

        result = client.publish(TOPIC, json.dumps(payload), qos=1)

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            cursor.execute(
                "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                (id_,)
            )
            conn.commit()

            print(f'✅ Uploaded & marked | id={id_} timestamp="{created_at}"')
            print(
                f"   AWS IoT sent: id={id_} | BP:{bp} | FP:{fp} | CR:{cr} | BC:{bc} | timestamp:{created_at}"
            )
        else:
            print("❌ Publish failed, RC:", result.rc)

        time.sleep(1)

except KeyboardInterrupt:
    print("🛑 Graceful shutdown")

finally:
    client.loop_stop()
    client.disconnect()
    conn.close()
