import sqlite3
import time
import json
import os

from awsiotsdk import mqtt_connection_builder
from awscrt import mqtt

# ---------------- BASE PATH ----------------
BASE_PATH = "/home/pi_123/data/src/pressure_project"

# ---------------- DATABASE PATH ----------------
DB_PATH = os.path.join(BASE_PATH, "db", "project.db")

# ---------------- AWS CERTIFICATE PATHS ----------------
AWS_IOT_DIR = os.path.join(BASE_PATH, "aws_iot")

CERT_PATH = os.path.join(
    AWS_IOT_DIR,
    "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-certificate.pem.crt"
)
KEY_PATH = os.path.join(
    AWS_IOT_DIR,
    "c5811382f2c2cfb311d53c99b4b0fadf4889674d37dd356864d17f059189a62d-private.pem.key"
)
CA_PATH = os.path.join(AWS_IOT_DIR, "AmazonRootCA1.pem")

# ---------------- VERIFY FILES ----------------
for f in [DB_PATH, CERT_PATH, KEY_PATH, CA_PATH]:
    if not os.path.exists(f):
        print("❌ Missing file:", f)
        exit(1)

print("✅ Database & certificates verified")

# ---------------- MQTT CONFIG ----------------
ENDPOINT  = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
CLIENT_ID = "RaspberryPi_Pressure"
TOPIC     = "brake/pressure"

# ---------------- CONNECT TO AWS IOT ----------------
def connect_mqtt():
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

mqtt_connection = connect_mqtt()

# ---------------- DATABASE SETUP ----------------
conn = sqlite3.connect(DB_PATH, timeout=10)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ---------------- AWS UPLOAD FUNCTION ----------------
def upload_to_app(row):
    payload = {
        "id": row["id"],
        "bp": row["bp_pressure"],
        "fp": row["fp_pressure"],
        "cr": row["cr_pressure"],
        "bc": row["bc_pressure"],
        "timestamp": row["created_at"]
    }

    mqtt_connection.publish(
        topic=TOPIC,
        payload=json.dumps(payload),
        qos=mqtt.QoS.AT_LEAST_ONCE
    )

    print(f"⬆️ Uploaded ID {row['id']}")
    return True

# ---------------- MAIN LOOP ----------------
while True:
    cursor.execute("""
        SELECT *
        FROM brake_pressure_log
        WHERE uploaded = 0
        ORDER BY created_at ASC
        LIMIT 1
    """)
    row = cursor.fetchone()

    if row:
        if upload_to_app(row):
            cursor.execute(
                "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                (row["id"],)
            )
            conn.commit()
            print(f"✅ Row {row['id']} marked uploaded")
    else:
        print("✅ No pending rows to upload")

    time.sleep(5)
