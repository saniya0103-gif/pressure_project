#!/usr/bin/env python3
import sqlite3
import time
import json
import ssl
import os
import paho.mqtt.client as mqtt
import sys

# ---------------- ENCODING SETUP ----------------
sys.stdout.reconfigure(encoding='utf-8')

# ---------------- DYNAMIC PATHS ----------------
BASE_PATH = "/app" if os.path.exists("/app") else os.path.dirname(os.path.abspath(__file__))
DB_FOLDER = os.path.join(BASE_PATH, "db")
DB_PATH   = os.path.join(DB_FOLDER, "project.db")
AWS_PATH  = os.path.join(BASE_PATH, "aws_iot")

print(f"Database folder: {DB_FOLDER}", flush=True)
print(f"Database file: {DB_PATH}", flush=True)

# ---------------- AWS CERT PATHS ----------------
CERT_PATH = os.path.join(AWS_PATH, "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-certificate.pem.crt")
KEY_PATH  = os.path.join(AWS_PATH, "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-private.pem.key")
CA_PATH   = os.path.join(AWS_PATH, "AmazonRootCA1.pem")  # make sure this exists

# ---------------- MQTT CONFIG ----------------
ENDPOINT  = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
PORT      = 8883
CLIENT_ID = "Raspberry"
TOPIC     = "brake/pressure"

# ---------------- MQTT CALLBACKS ----------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core", flush=True)
    else:
        print(f"❌ MQTT connection failed, RC={rc}", flush=True)

def on_publish(client, userdata, mid):
    print("📤 Data published to AWS IoT", flush=True)

# ---------------- CONNECT TO AWS ----------------
def connect_mqtt():
    try:
        client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
        client.on_connect = on_connect
        client.on_publish = on_publish

        client.tls_set(
            ca_certs=CA_PATH,
            certfile=CERT_PATH,
            keyfile=KEY_PATH,
            tls_version=ssl.PROTOCOL_TLSv1_2
        )

        print("Connecting to AWS IoT Core...", flush=True)
        client.connect(ENDPOINT, PORT, keepalive=60)
        client.loop_start()
        return client
    except Exception as e:
        print(f"❌ MQTT connection failed: {e}", flush=True)
        return None

# ---------------- WAIT FOR MQTT CONNECTION ----------------
mqtt_client = None
while mqtt_client is None:
    mqtt_client = connect_mqtt()
    if mqtt_client is None:
        print("Retrying MQTT connection in 5 seconds...", flush=True)
        time.sleep(5)

# ---------------- DATABASE SETUP ----------------
os.makedirs(DB_FOLDER, exist_ok=True)
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# ---------------- UPLOAD FUNCTION ----------------
def upload_to_app(row):
    try:
        payload = {
            "bp_pressure": row["bp_pressure"],
            "fp_pressure": row["fp_pressure"],
            "cr_pressure": row["cr_pressure"],
            "bc_pressure": row["bc_pressure"],
            "created_at": row["created_at"]
        }
        mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)
        print(f"Sent to AWS IoT: {payload}", flush=True)
        return True
    except Exception as e:
        print(f"❌ Upload failed: {e}", flush=True)
        return False

# ---------------- MAIN LOOP ----------------
while True:
    cur.execute("""
        SELECT * FROM brake_pressure_log
        WHERE uploaded = 0
        ORDER BY created_at ASC
        LIMIT 1
    """)
    row = cur.fetchone()

    if row:
        if upload_to_app(row):
            cur.execute(
                "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                (row['id'],)
            )
            conn.commit()
            print(f"Row {row['id']} marked uploaded ✅", flush=True)
    else:
        print("No data to upload", flush=True)

    time.sleep(2)
