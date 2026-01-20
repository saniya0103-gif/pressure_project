import sqlite3
import json
import time
import os
import ssl
import sys
import paho.mqtt.client as mqtt

# ================= BASE PATH =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "project.db")
CERT_DIR = os.path.join(BASE_DIR, "aws_iot")

# Use the actual filenames from your aws_iot folder
ROOT_CA = os.path.join(CERT_DIR, "AmazonRootCA1.pem")
CERT_FILE = os.path.join(CERT_DIR, "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-certificate.pem.crt")
KEY_FILE = os.path.join(CERT_DIR, "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-private.pem.key")

# ================= AWS CONFIG =================
AWS_ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
CLIENT_ID = "Raspberry"
TOPIC = "brake/pressure"
PORT = 8883

# ================= VALIDATION =================
print("Checking DB & certificate paths...")

missing = False
for f in [ROOT_CA, CERT_FILE, KEY_FILE]:
    if not os.path.exists(f):
        print("❌ Missing:", f)
        missing = True

if missing:
    print("\n❌ AWS IoT certificates are mandatory for port 8883")
    print("👉 Place files inside aws_iot/ directory")
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

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core")
    else:
        print("❌ Connection failed, rc =", rc)

client.on_connect = on_connect

print("Connecting to AWS IoT Core...")
try:
    client.connect(AWS_ENDPOINT, PORT)
except Exception as e:
    print("❌ MQTT Connection Error:", e)
    sys.exit(1)

client.loop_start()

# ================= DATABASE =================
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# ================= MAIN LOOP =================
try:
    while True:
        cur.execute("""
            SELECT *
            FROM brake_pressure_log
            WHERE uploaded = 0
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
                "created_at": row["created_at"],
                "bp_pressure": row["bp_pressure"],
                "fp_pressure": row["fp_pressure"],
                "cr_pressure": row["cr_pressure"],
                "bc_pressure": row["bc_pressure"]
            }

            try:
                result = client.publish(TOPIC, json.dumps(payload), qos=1)

                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    print("Sent to AWS IoT:", payload)

                    cur.execute(
                        "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                        (row["id"],)
                    )
                    conn.commit()

                    print(
                        f"Uploaded and marked DB uploaded=1 | "
                        f"Timestamp: {row['created_at']}"
                    )
                    print("Data published to AWS IoT\n")
                else:
                    print("❌ Publish failed, retry later")
                    break

            except Exception as e:
                print("❌ Exception while publishing:", e)
                break

        time.sleep(2)

except KeyboardInterrupt:
    print("Process stopped by user")

finally:
    conn.close()
    client.loop_stop()
    client.disconnect()
    print("Database closed and MQTT disconnected")
