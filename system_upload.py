import sqlite3
import json
import time
import os
import ssl
import sys
import paho.mqtt.client as mqtt
import traceback

# ---------------- BASE PATH ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "project.db")

# ---------------- AWS IoT CERTIFICATES ----------------
CERT_DIR = os.path.expanduser("~/aws_certs")

ROOT_CA = os.path.join(CERT_DIR, "AmazonRootCA3.pem")
CERT_FILE = os.path.join(CERT_DIR, "0a0f7d38323fdef876a81f1a8d6671502e80d50d6e2fdc753a68baa51cfcf5ef-certificate.pem.crt")
KEY_FILE = os.path.join(CERT_DIR, "0a0f7d38323fdef876a81f1a8d6671502e80d50d6e2fdc753a68baa51cfcf5ef-private.pem.key")

CLIENT_ID = "Raspberry_pi"
AWS_ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"  # e.g., amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com
PORT = 8883
TOPIC = "brake/pressure"


# ---------------- VERIFY FILES ----------------
for f in [ROOT_CA, CERT_FILE, KEY_FILE, DB_PATH]:
    if not os.path.isfile(f):
        print("Missing file:", f, flush=True)
        sys.exit(1)

print("All files verified", flush=True)

# ---------------- MQTT SETUP ----------------
client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
client.tls_set(
    ca_certs=ROOT_CA,
    certfile=CERT_FILE,
    keyfile=KEY_FILE,
    tls_version=ssl.PROTOCOL_TLSv1_2
)

connected = False
published_flag = False

def on_connect(client, userdata, flags, rc):
    global connected
    if rc == 0:
        connected = True
        print("Connected to AWS IoT Core", flush=True)
    else:
        print("MQTT connect failed rc =", rc, flush=True)

def on_disconnect(client, userdata, rc):
    global connected
    connected = False
    print("MQTT disconnected rc =", rc, flush=True)

def on_publish(client, userdata, mid):
    global published_flag
    published_flag = True

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_publish = on_publish

# ---------------- CONNECT ----------------
while not connected:
    try:
        client.connect(AWS_ENDPOINT, PORT, keepalive=60)
        client.loop_start()
        time.sleep(1)
    except Exception as e:
        print("MQTT connection error:", e, flush=True)
        time.sleep(5)  # wait and retry

# ---------------- DATABASE SETUP ----------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

try:
    while True:
        try:
            cur.execute("""
                SELECT *
                FROM brake_pressure_log
                WHERE uploaded = 0
                ORDER BY created_at ASC
                LIMIT 5
            """)
            rows = cur.fetchall()

            if not rows:
                print("No pending rows", flush=True)
                time.sleep(5)
                continue

            for row in rows:
                payload = {
                    "timestamp": row["created_at"],
                    "bp_pressure": row["bp_pressure"],
                    "fp_pressure": row["fp_pressure"],
                    "cr_pressure": row["cr_pressure"],
                    "bc_pressure": row["bc_pressure"]
                }

                payload_str = json.dumps(payload)

                print(
                    f"⬆️ Uploading | ID:{row['id']} | "
                    f"BP:{row['bp_pressure']} FP:{row['fp_pressure']} "
                    f"CR:{row['cr_pressure']} BC:{row['bc_pressure']} | "
                    f"time:{row['created_at']}",
                    flush=True
                )

                published_flag = False
                client.publish(TOPIC, payload_str, qos=1)

                timeout = time.time() + 5
                while not published_flag:
                    if time.time() > timeout:
                        print(f"Publish timeout for ID:{row['id']}, retrying later", flush=True)
                        break
                    time.sleep(0.1)

                else:
                    cur.execute(
                        "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                        (row["id"],)
                    )
                    conn.commit()
                    print(f"Uploaded & marked id={row['id']}\n", flush=True)

            time.sleep(2)  # small sleep to reduce CPU usage

        except Exception:
            print("Error during upload loop:", flush=True)
            traceback.print_exc()
            time.sleep(5)  # wait before retrying

except KeyboardInterrupt:
    print("Stopped by user", flush=True)

finally:
    conn.close()
    client.loop_stop()
    client.disconnect()
    print("Database closed & MQTT disconnected", flush=True)
