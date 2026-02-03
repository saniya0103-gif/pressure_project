import sqlite3
import json
import time
import os
import ssl
import sys
import paho.mqtt.client as mqtt

# ================= BASE PATH =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "project.db")
CERT_DIR = os.path.join(BASE_DIR, "aws_iot")

# ================= AWS IoT CERTIFICATES =================
ROOT_CA = os.path.join(CERT_DIR, "AmazonRootCA1.pem")
CERT_FILE = os.path.join(CERT_DIR, "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-certificate.pem.crt")
KEY_FILE = os.path.join(CERT_DIR, "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-private.pem.key")

# ================= AWS IoT SETTINGS =================
AWS_ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
CLIENT_ID = "Raspberry"
TOPIC = "brake/pressure"
PORT = 8883

# ================= VALIDATION =================
print("Checking DB & certificate paths...")

for f in [ROOT_CA, CERT_FILE, KEY_FILE]:
    if not os.path.exists(f):
        print("❌ Missing:", f)
        sys.exit(1)

if not os.path.exists(DB_PATH):
    print("❌ Database not found:", DB_PATH)
    sys.exit(1)

print("✅ All required files found")

# ================= MQTT SETUP =================
client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)

client.tls_set(
    ca_certs=ROOT_CA,
    certfile=CERT_FILE,
    keyfile=KEY_FILE,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

connected_flag = False

def on_connect(client, userdata, flags, rc):
    global connected_flag
    if rc == 0:
        print("✅ Connected to AWS IoT Core")
        connected_flag = True
    else:
        print("❌ Connection failed, rc =", rc)

client.on_connect = on_connect

client.connect(AWS_ENDPOINT, PORT)
client.loop_start()

while not connected_flag:
    time.sleep(1)

# ================= DATABASE =================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# ✅ VERY IMPORTANT: Enable WAL (fixes race condition)
cur.execute("PRAGMA journal_mode=WAL;")
cur.execute("PRAGMA synchronous=NORMAL;")
conn.commit()

# ================= MAIN LOOP =================
try:
    while True:
        # 🔒 Read only fully-written rows (2s safety window)
        cur.execute("""
            SELECT *
            FROM brake_pressure_log
            WHERE uploaded = 0
              AND created_at <= datetime('now', '-2 seconds')
            ORDER BY created_at ASC
            LIMIT 5
        """)
        rows = cur.fetchall()

        if not rows:
            print("✅ No pending rows")
            time.sleep(5)
            continue

        for row in rows:
            payload = {
                "ID": "Sensor1",
                "Timestamp": row["created_at"],
                "bp_pressure": row["bp_pressure"],
                "fp_pressure": row["fp_pressure"],
                "cr_pressure": row["cr_pressure"],
                "bc_pressure": row["bc_pressure"],
                "sent_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            print(
                f"[UPLOAD] id={row['id']} "
                f"BP={row['bp_pressure']} FP={row['fp_pressure']} "
                f"CR={row['cr_pressure']} BC={row['bc_pressure']} "
                f"time={row['created_at']}"
            )

            result = client.publish(TOPIC, json.dumps(payload), qos=1)

            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                # ✅ Atomic update (prevents double upload)
                cur.execute("""
                    UPDATE brake_pressure_log
                    SET uploaded = 1
                    WHERE id = ? AND uploaded = 0
                """, (row["id"],))
                conn.commit()

                print(f"✅ Uploaded & marked id={row['id']}\n")
            else:
                print("❌ Publish failed, retry later")
                break

        time.sleep(2)

except KeyboardInterrupt:
    print("Stopped by user")

finally:
    conn.close()
    client.loop_stop()
    client.disconnect()
    print("Database closed and MQTT disconnected")
