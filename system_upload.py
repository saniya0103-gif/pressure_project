import os
import ssl
import time
import json
import sqlite3
import paho.mqtt.client as mqtt

# =========================
# AWS IOT CONFIG
# =========================
AWS_ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
CLIENT_ID = "Raspberry_pi"
TOPIC = "brake/pressure"

# =========================
# PATH HANDLING (SMART)
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# If running in Docker
RASPI_DIR = "/app/raspi" if os.path.exists("/app/raspi") else os.path.join(BASE_DIR, "raspi")

CA_FILE = os.path.join(RASPI_DIR, "AmazonRootCA1.pem")
CERT_FILE = os.path.join(RASPI_DIR, "3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-certificate.pem.crt")
KEY_FILE = os.path.join(RASPI_DIR, "3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-private.pem.key")

DB_PATH = os.path.join(BASE_DIR, "db", "project.db")

# =========================
# DEBUG CHECK (NO GUESSING)
# =========================
print("=== DEBUG START ===")
print("DB exists:", os.path.exists(DB_PATH))
print("CA exists:", os.path.exists(CA_FILE))
print("CERT exists:", os.path.exists(CERT_FILE))
print("KEY exists:", os.path.exists(KEY_FILE))
print("RASPI DIR:", RASPI_DIR)
print("=== DEBUG END ===")

# =========================
# MQTT CALLBACKS
# =========================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ MQTT Connected to AWS IoT")
    else:
        print("❌ MQTT Connection failed, rc =", rc)

def on_disconnect(client, userdata, rc):
    print("⚠ MQTT disconnected, rc =", rc)

# =========================
# MQTT CLIENT SETUP
# =========================
client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
client.on_connect = on_connect
client.on_disconnect = on_disconnect

client.tls_set(
    ca_certs=CA_FILE,
    certfile=CERT_FILE,
    keyfile=KEY_FILE,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

client.tls_insecure_set(False)

# Auto reconnect (IMPORTANT)
client.reconnect_delay_set(min_delay=1, max_delay=60)

client.connect(AWS_ENDPOINT, 8883, keepalive=60)
client.loop_start()

# =========================
# DATABASE LOOP
# =========================
while True:
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()

        cur.execute("""
            SELECT id, bp_pressure, fp_pressure, cr_pressure, bc_pressure, created_at
            FROM brake_pressure_log
            WHERE uploaded = 0
            ORDER BY id ASC
            LIMIT 1
        """)

        row = cur.fetchone()

        if row:
            record_id, bp, fp, cr, bc, created_at = row

            payload = {
                "bp_pressure": bp,
                "fp_pressure": fp,
                "cr_pressure": cr,
                "bc_pressure": bc,
                "time": created_at
            }

            client.publish(TOPIC, json.dumps(payload), qos=1)

            cur.execute(
                "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                (record_id,)
            )
            conn.commit()

            print(f"✅ Uploaded & marked | id={record_id}  AWS IoT sent: "
                  f"BP:{bp} | FP:{fp} | CR:{cr} | BC:{bc} | time:{created_at}")

        conn.close()
        time.sleep(5)

    except Exception as e:
        print("❌ ERROR:", e)
        time.sleep(5)
