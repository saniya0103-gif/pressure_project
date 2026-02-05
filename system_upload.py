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

# ================= AWS IoT CERTIFICATES =================
ROOT_CA = os.path.join(CERT_DIR, "AmazonRootCA1.pem")

CERT_FILE = os.path.join(
    CERT_DIR,
    "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-certificate.pem.crt"
)

KEY_FILE = os.path.join(
    CERT_DIR,
    "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-private.pem.key"
)

# ================= AWS IoT SETTINGS =================
AWS_ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
CLIENT_ID = "Raspberry"
TOPIC = "brake/pressure"
PORT = 8883

# ================= VERIFY FILES =================
required_files = [ROOT_CA, CERT_FILE, KEY_FILE, DB_PATH]

for f in required_files:
    if not os.path.isfile(f):
        print("Missing file:", f, flush=True)
        sys.exit(1)

print("All files verified", flush=True)

# ================= MQTT SETUP =================
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

# ================= CONNECT =================
try:
    client.connect(AWS_ENDPOINT, PORT, keepalive=60)
except Exception as e:
    print("MQTT connection error:", e, flush=True)
    sys.exit(1)

client.loop_start()

while not connected:
    print("Waiting for MQTT connection...", flush=True)
    time.sleep(1)

# ================= DATABASE =================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
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
            print("No pending rows", flush=True)
            time.sleep(5)
            continue

        for row in rows:
            payload = {
                "sensor_id": row["sensor_id"],
                "timestamp": row["created_at"],
                "bp_raw": row["bp_raw"],
                "fp_raw": row["fp_raw"],
                "cr_raw": row["cr_raw"],
                "bc_raw": row["bc_raw"]
            }

            payload_str = json.dumps(payload)

            print(
                f"⬆️ Uploading | ID:{row['sensor_id']} | "
                f"BP:{row['bp_raw']} FP:{row['fp_raw']} "
                f"CR:{row['cr_raw']} BC:{row['bc_raw']} | "
                f"time:{row['created_at']}",
                flush=True
            )

            published_flag = False
            client.publish(TOPIC, payload_str, qos=1)

            timeout = time.time() + 5
            while not published_flag:
                if time.time() > timeout:
                    raise Exception("Publish timeout")
                time.sleep(0.1)

            cur.execute(
                "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                (row["id"],)
            )
            conn.commit()

            print(f"Uploaded & marked id={row['id']}\n", flush=True)

        time.sleep(2)

except KeyboardInterrupt:
    print("Stopped by user", flush=True)

finally:
    conn.close()
    client.loop_stop()
    client.disconnect()
    print("🔌 Database closed & MQTT disconnected", flush=True)
