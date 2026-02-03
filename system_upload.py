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

# ================= VERIFY FILES =================
for f in [ROOT_CA, CERT_FILE, KEY_FILE, DB_PATH]:
    if not os.path.exists(f):
        print("Missing:", f)
        sys.exit(1)

print("All files verified")

# ================= MQTT SETUP =================
client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
client.tls_set(
    ca_certs=ROOT_CA,
    certfile=CERT_FILE,
    keyfile=KEY_FILE,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

connected = False

def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        connected = True
        print("Connected to AWS IoT Core")
    else:
        print("MQTT connect failed rc =", rc)

def on_disconnect(client, userdata, rc):
    global connected
    connected = False
    print("MQTT disconnected rc =", rc)

client.on_connect = on_connect
client.on_disconnect = on_disconnect

# ================= CONNECT =================
try:
    client.connect(AWS_ENDPOINT, PORT, keepalive=60)
except Exception as e:
    print("MQTT connection error:", e)
    sys.exit(1)

client.loop_start()

while not connected:
    print("Waiting for MQTT connection...")
    time.sleep(1)

# ================= DATABASE =================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Recommended for Docker + SQLite
cur.execute("PRAGMA journal_mode=WAL;")
cur.execute("PRAGMA synchronous=NORMAL;")
conn.commit()

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
            print("No pending rows")
            time.sleep(5)
            continue

        for row in rows:
            # Ensure MQTT is connected
            if not client.is_connected():
                print("MQTT not connected, trying to reconnect...")
                try:
                    client.reconnect()
                    time.sleep(2)
                except Exception as e:
                    print("Reconnect failed:", e)
                    break

            payload = {
                "created_at": row["created_at"],
                "bp_pressure": row["bp_pressure"],
                "fp_pressure": row["fp_pressure"],
                "cr_pressure": row["cr_pressure"],
                "bc_pressure": row["bc_pressure"],
                #"sent_at": time.strftime("%Y-%m-%d %H:%M:%S")
            }

            payload_str = json.dumps(payload)

            # Print summary + exact JSON sent
            print(f"[UPLOAD] id={row['id']} BP={row['bp_pressure']} FP={row['fp_pressure']} CR={row['cr_pressure']} BC={row['bc_pressure']}")
            print(f"📡 Sending payload to AWS IoT: {payload_str}")

            try:
                msg = client.publish(TOPIC, payload_str, qos=1)
                msg.wait_for_publish(timeout=5)

                if msg.rc == mqtt.MQTT_ERR_SUCCESS:
                    cur.execute("""
                        UPDATE brake_pressure_log
                        SET uploaded = 1
                        WHERE id = ? AND uploaded = 0
                    """, (row["id"],))
                    conn.commit()
                    print(f"✅ Uploaded & marked id={row['id']}\n")
                else:
                    print("Publish failed, will retry later")
                    break

            except Exception as e:
                print("Exception while publishing:", e)
                break

        time.sleep(2)

except KeyboardInterrupt:
    print("Stopped by user")

finally:
    conn.close()
    client.loop_stop()
    client.disconnect()
    print("Database closed and MQTT disconnected")
