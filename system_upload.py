import sqlite3
import time
import json
import os

from awsiot import mqtt_connection_builder
from awscrt import mqtt

# ---------------- BASE DIRECTORY ----------------
BASE_DIR = "/home/pi_123/aws_iot"   # <-- updated path

# ---------------- CERTIFICATE PATHS ----------------
CERT_PATH = "/app/aws_iot/device.cert.pem"
KEY_PATH  = "/app/aws_iot/device.private.key"
CA_PATH   = "/app/aws_iot/AmazonRootCA1.pem"

# ---------------- MQTT CONFIG ----------------
ENDPOINT  = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
CLIENT_ID = "Raspberry"
TOPIC     = "brake/pressure"

# ---------------- CONNECT TO AWS IOT ----------------
def connect_mqtt():
    try:
        mqtt_connection = mqtt_connection_builder.mtls_from_path(
            endpoint=ENDPOINT,
            cert_filepath=CERT_PATH,
            pri_key_filepath=KEY_PATH,
            ca_filepath=CA_PATH,
            client_id=CLIENT_ID,
            clean_session=False,
            keep_alive_secs=30
        )
        print("Connecting to AWS IoT Core...")
        mqtt_connection.connect().result()
        print("✅ Connected to AWS IoT Core")
        return mqtt_connection
    except Exception as e:
        print(" MQTT connection failed:", e)
        return None

mqtt_connection = None
while mqtt_connection is None:
    mqtt_connection = connect_mqtt()
    if mqtt_connection is None:
        print("Retrying connection in 5 seconds...")
        time.sleep(5)

# ------------------ DATABASE SETUP ------------------
DB_PATH = "project.db"
time.sleep(2)

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ------------------ AWS UPLOAD FUNCTION ------------------
def upload_to_app(row):
    try:
        payload = {
            "bp_pressure": row["bp_pressure"],
            "fp_pressure": row["fp_pressure"],
            "cr_pressure": row["cr_pressure"],
            "bc_pressure": row["bc_pressure"],
            "created_at": row["created_at"]
        }

        mqtt_connection.publish(
            topic=TOPIC,
            payload=json.dumps(payload),
            qos=mqtt.QoS.AT_LEAST_ONCE
        )

        print("Sent to AWS IoT:", payload)
        return True

    except Exception as e:
        print("Upload failed:", e)
        return False

# ------------------ MAIN LOOP ------------------
while True:
    cursor.execute("""
        SELECT * FROM brake_pressure_log
        WHERE uploaded = 0
        ORDER BY created_at ASC
        LIMIT 1
    """)
    row = cursor.fetchone()

    if row:
        success = upload_to_app(row)
        if success:
            cursor.execute("""
                UPDATE brake_pressure_log
                SET uploaded = 1
                WHERE id = ?
            """, (row["id"],))
            conn.commit()
            print("Uploaded and marked as done ✅")
    else:
        print("No pending rows to upload.")

    time.sleep(5)
