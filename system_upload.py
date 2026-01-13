#!/home/pi_123/data/src/pressure_project/venv311/bin/python

import sqlite3
import time
import json
import ssl
import paho.mqtt.client as mqtt
import os

timesleep(10)
# ---------------- CERTIFICATE PATHS ----------------
CERT_PATH = "/home/pi_123/data/src/pressure_project/aws_iot/c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-certificate.pem.crt"
KEY_PATH  = "/home/pi_123/data/src/pressure_project/aws_iot/c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-private.pem.key"
CA_PATH   = "/home/pi_123/data/src/pressure_project/aws_iot/AmazonRootCA1.pem"

# ---------------- MQTT CONFIG ----------------
ENDPOINT  = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
PORT      = 8883
CLIENT_ID = "Raspberry"
TOPIC     = "brake/pressure"

# ---------------- MQTT CALLBACKS ----------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connecting to AWS IoT Core...")
        print("✅ Connected to AWS IoT Core")
    else:
        print("❌ MQTT connection failed, RC =", rc)

def on_publish(client, userdata, mid):
    print("📤 Data published to AWS IoT")

# ---------------- CONNECT TO AWS IOT ----------------
def connect_mqtt():
    try:
        client = mqtt.Client(client_id=CLIENT_ID)
        client.on_connect = on_connect
        client.on_publish = on_publish

        client.tls_set(
            ca_certs=CA_PATH,
            certfile=CERT_PATH,
            keyfile=KEY_PATH,
            tls_version=ssl.PROTOCOL_TLSv1_2
        )

        client.connect(ENDPOINT, PORT, keepalive=60)
        client.loop_start()
        return client

    except Exception as e:
        print("MQTT connection failed:", e)
        return None

mqtt_client = None
while mqtt_client is None:
    mqtt_client = connect_mqtt()
    if mqtt_client is None:
        print("Retrying connection in 5 seconds...")
        time.sleep(10)

# ------------------ DATABASE SETUP ------------------
DB_PATH = "project.db"
time.sleep(10)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ------------------ AWS UPLOAD FUNCTION ------------------
def upload_to_app(row):
    try:
        payload = {
            "created_at": row["created_at"],
            "bp_pressure": row["bp_pressure"],
            "fp_pressure": row["fp_pressure"],
            "cr_pressure": row["cr_pressure"],
            "bc_pressure": row["bc_pressure"],
            "uploaded_db": row["uploaded"],      # DB status (0 or 1)
            "aws_status": "uploaded"             # AWS status
        }

        mqtt_client.publish(
            TOPIC,
            json.dumps(payload),
            qos=1
        )

        print("Sent to AWS IoT:", payload)
        return True

    except Exception as e:
        print("Upload failed:", e)
        return False

# ------------------ MAIN LOOP ------------------
while True:
    # fetch rows in order of created_at (oldest first)
    cursor.execute("""
        SELECT * FROM brake_pressure_log
        ORDER BY created_at ASC
    """)
    rows = cursor.fetchall()

    pending_found = False
    for row in rows:
        if row["uploaded"] == 0:  # only upload pending rows
            pending_found = True
            success = upload_to_app(row)
            if success:
                cursor.execute("""
                    UPDATE brake_pressure_log
                    SET uploaded = 1
                    WHERE id = ?
                """, (row["id"],))
                conn.commit()
                print(f"Uploaded and marked as done ✅ | DB uploaded=1 | Timestamp: {row['created_at']}")

                # ----------------- Delay per row -----------------
                time.sleep(10)  # wait 2 seconds before next row

    if not pending_found:
        print("No pending rows to upload (all uploaded).")

    # delay before checking DB again
    time.sleep(15)