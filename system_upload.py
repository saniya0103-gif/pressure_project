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
CERT_FILE = os.path.join(CERT_DIR, "device-certificate.pem.crt")
KEY_FILE = os.path.join(CERT_DIR, "private.pem.key")

# ================= AWS IoT SETTINGS =================
AWS_ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
CLIENT_ID = "Raspberry_Uploader"
TOPIC = "brake/pressure"
PORT = 8883

# ================= VERIFY FILES =================
for f in [ROOT_CA, CERT_FILE, KEY_FILE, DB_PATH]:
    if not os.path.exists(f):
        print("Missing file:", f)
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
    print("⚠ MQTT disconnected rc =", rc, flush=True)

def on_publish(client, userdata, mid):
    global published_flag
    published_flag = True

client.on_connect = on_connect
client.on_disconnect = on_disconnect
client.on_publish = on_publish

# ================= CONNECT =================
client.connect(AWS_ENDPOINT, PORT, keepalive=60)
client.loop_start()

while not connected:
    print("Waiting for MQTT connection...", flush=True)
    time.sleep(1)

# ================= DATABASE =================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()
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
            print("No pending rows", flush=True)
            time.sleep(5)
            continue

        for row in rows:
            if not client.is_connected():
                print("MQTT disconnected, reconnecting...", flush=True)
                client.reconnect()
                time.sleep(2)

            payload = {
                "sensor_id": row["sensor_id"],
                "timestamp": row["created_at"],
                "bp_pressure": row["bp_pressure"],
                "fp_pressure": row["fp_pressure"],
                "cr_pressure": row["cr_pressure"],
                "bc_pressure": row["bc_pressure"]
            }

            payload_str = json.dumps(payload)

            print(
                f"RAW VALUES | ID:{row['sensor_id']} | "
                f"BP:{row['bp_pressure']} | FP:{row['fp_pressure']} | "
                f"CR:{row['cr_pressure']} | BC:{row['bc_pressure']} | "
                f"timestamp : {row['created_at']} | Uploading",
                flush=True
            )

            published_flag = False
            client.publish(TOPIC, payload_str, qos=1)

            timeout = time.time() + 5
            while not published_flag:
                if time.time() > timeout:
                    raise Exception("Publish timeout")
                time.sleep(0.1)

            cur.execute("""
                UPDATE brake_pressure_log
                SET uploaded = 1
                WHERE id = ?
            """, (row["id"],))
            conn.commit()

            print("Uploaded & marked\n", flush=True)

        time.sleep(2)

except KeyboardInterrupt:
    print("Stopped by user", flush=True)

finally:
    conn.close()
    client.loop_stop()
    client.disconnect()
    print("Database closed & MQTT disconnected", flush=True)
