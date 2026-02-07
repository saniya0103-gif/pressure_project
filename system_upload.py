import os
import time
import json
import sqlite3
import ssl
import paho.mqtt.client as mqtt

# ================= PATH RESOLUTION =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "db", "project.db")

CERT_DIR = os.path.join(BASE_DIR, "raspi")

CA_PATH = os.path.join(CERT_DIR, "AmazonRootCA1 (4).pem")
CERT_PATH = os.path.join(
    CERT_DIR,
    "3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-certificate.pem.crt"
)
KEY_PATH = os.path.join(
    CERT_DIR,
    "3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-private.pem.key"
)

# ================= AWS DETAILS =================
AWS_ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
AWS_PORT = 8883
CLIENT_ID = "Raspberry_pi"
TOPIC = "brake/pressure"

# ================= DEBUG =================
print("\n=== DEBUG START ===")
print("BASE_DIR:", BASE_DIR)
print("DB exists:", os.path.exists(DB_PATH))
print("CA exists:", os.path.exists(CA_PATH))
print("CERT exists:", os.path.exists(CERT_PATH))
print("KEY exists:", os.path.exists(KEY_PATH))
print("=== DEBUG END ===\n")

if not all(map(os.path.exists, [DB_PATH, CA_PATH, CERT_PATH, KEY_PATH])):
    raise FileNotFoundError("❌ One or more required files missing")

# ================= MQTT =================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core")
    else:
        print("❌ MQTT connect failed, RC:", rc)

client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
client.on_connect = on_connect

client.tls_set(
    ca_certs=CA_PATH,
    certfile=CERT_PATH,
    keyfile=KEY_PATH,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

client.connect(AWS_ENDPOINT, AWS_PORT, 60)
client.loop_start()

# ================= UPLOAD LOOP =================
while True:
    try:
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

            client.publish(TOPIC, json.dumps(payload), qos=1)

            print(
                f"✅ Uploaded & marked | id={r[0]}  AWS IoT sent: "
                f"BP:{r[1]} | FP:{r[2]} | CR:{r[3]} | BC:{r[4]} | time:{r[5]}"
            )

            cursor.execute(
                "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                (r[0],)
            )
            conn.commit()

        conn.close()
        time.sleep(5)

    except Exception as e:
        print("⚠ Upload error:", e)
        time.sleep(5)
