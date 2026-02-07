import os
import ssl
import json
import time
import signal
import sys
import sqlite3
import paho.mqtt.client as mqtt

# =========================
# CONFIG
# =========================
BASE_PATH = os.getcwd()

DB_PATH = os.path.join(BASE_PATH, "db", "project.db")
CERT_PATH = os.path.join(BASE_PATH, "raspi", "3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-certificate.pem.crt")
KEY_PATH  = os.path.join(BASE_PATH, "raspi", "3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-private.pem.key")
CA_PATH   = os.path.join(BASE_PATH, "raspi", "AmazonRootCA1 (4).pem")

AWS_ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
AWS_PORT = 8883
CLIENT_ID = "Raspberry_pi"
TOPIC = "brake/pressure"

POLL_DELAY = 5  # seconds

# =========================
# DEBUG CHECK
# =========================
print("=== DEBUG START ===")
print("PWD:", BASE_PATH)
print("DB exists:", os.path.exists(DB_PATH))
print("CA exists:", os.path.exists(CA_PATH))
print("CERT exists:", os.path.exists(CERT_PATH))
print("KEY exists:", os.path.exists(KEY_PATH))
print("=== DEBUG END ===")

# =========================
# MQTT SETUP
# =========================
client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)

client.tls_set(
    ca_certs=CA_PATH,
    certfile=CERT_PATH,
    keyfile=KEY_PATH,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

client.tls_insecure_set(False)

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core")
    else:
        print("❌ MQTT connect failed, RC:", rc)

client.on_connect = on_connect

client.connect(AWS_ENDPOINT, AWS_PORT, 60)

# =========================
# GRACEFUL SHUTDOWN
# =========================
def shutdown(sig, frame):
    print("🛑 Graceful shutdown")
    try:
        client.disconnect()
    except:
        pass
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# =========================
# MAIN LOOP
# =========================
while True:
    client.loop(timeout=1.0)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, bp_pressure, fp_pressure, cr_pressure, bc_pressure, created_at
        FROM brake_pressure_log
        WHERE uploaded = 0
        ORDER BY id ASC
        LIMIT 5
    """)
    rows = cursor.fetchall()

    for r in rows:
        payload = {
            "id": r[0],
            "bp": r[1],
            "fp": r[2],
            "cr": r[3],
            "bc": r[4],
            "timestamp": r[5]
        }

        result = client.publish(TOPIC, json.dumps(payload), qos=1)

        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            cursor.execute(
                "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                (r[0],)
            )
            conn.commit()

            print(
                f"✅ Uploaded & marked | id={r[0]}  AWS IoT sent: "
                f"BP:{r[1]} | FP:{r[2]} | CR:{r[3]} | BC:{r[4]} | time:{r[5]}"
            )

    conn.close()
    time.sleep(POLL_DELAY)
