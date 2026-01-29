import sqlite3
import json
import time
import os
import ssl
import sys
import paho.mqtt.client as mqtt

# ================= BASE PATH =================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "project.db")  # Mounted db folder in Docker
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

missing = False
for f in [ROOT_CA, CERT_FILE, KEY_FILE]:
    if not os.path.exists(f):
        print("❌ Missing:", f)
        missing = True

if missing:
    print("\n❌ AWS IoT certificates are mandatory")
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

# ===== Connection Flag =====
connected_flag = False

def on_connect(client, userdata, flags, rc):
    global connected_flag
    if rc == 0:
        print("✅ Connected to AWS IoT Core")
        connected_flag = True
    else:
        print("❌ Connection failed, rc =", rc)
        connected_flag = False

client.on_connect = on_connect

try:
    print("Connecting to AWS IoT Core...")
    client.connect(AWS_ENDPOINT, PORT)
except Exception as e:
    print("❌ MQTT Connection Error:", e)
    sys.exit(1)

client.loop_start()

# ===== Wait until connected =====
while not connected_flag:
    print("⏳ Waiting for MQTT connection...")
    time.sleep(1)

# ================= DATABASE =================
try:
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
except sqlite3.OperationalError as e:
    print("❌ Unable to open database:", e)
    sys.exit(1)

conn.row_factory = sqlite3.Row
cur = conn.cursor()

# ================= MAIN LOOP =================
try:
    while True:
        # Fetch pending rows, oldest first
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
                "ID": "Sensor1",
                "Timestamp": row["created_at"],
                "bp_pressure": row["bp_pressure"],
                "fp_pressure": row["fp_pressure"],
                "cr_pressure": row["cr_pressure"],
                "bc_pressure": row["bc_pressure"]
            }

            try:
                result = client.publish(TOPIC, json.dumps(payload), qos=1)

                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    print(f"Sent to AWS IoT: {payload}")
                    # ✅ Correctly mark as uploaded
                    cur.execute(
                        "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                        (row["id"],)
                    )
                    conn.commit()
                    print(f"Uploaded and marked ROW id = {row['id']} | Timestamp: {row['created_at']}")
                    print("Data published to AWS IoT\n")
                else:
                    print("❌ Publish failed, will retry later | rc =", result.rc)
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
