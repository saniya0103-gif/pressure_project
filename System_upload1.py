import sqlite3
import time
import os
import json
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# ---------------- DEVICE CONFIG ----------------
DEVICE_ID = "raspi_1"   # Keep constant per device
CLIENT_ID = "Raspberry4_1"
ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
TOPIC = "brake/data"
PORT = 8883

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------- CERTIFICATE PATH ----------------
ROOT_CA = os.path.join(BASE_DIR, "certs", "AmazonRootCA1.pem")
PRIVATE_KEY = os.path.join(BASE_DIR, "certs", "private.pem.key")
CERTIFICATE = os.path.join(BASE_DIR, "certs", "certificate.pem.crt")

# ---------------- MQTT CLIENT ----------------
mqtt_client = AWSIoTMQTTClient(CLIENT_ID)
mqtt_client.configureEndpoint(ENDPOINT, PORT)
mqtt_client.configureCredentials(ROOT_CA, PRIVATE_KEY, CERTIFICATE)

mqtt_client.configureOfflinePublishQueueing(-1)
mqtt_client.configureDrainingFrequency(2)
mqtt_client.configureConnectDisconnectTimeout(10)
mqtt_client.configureMQTTOperationTimeout(5)

print("🔐 Connecting to AWS IoT...")
mqtt_client.connect()
print("Connected to AWS IoT\n")

# ---------------- DATABASE ----------------
DB_PATH = os.path.join(BASE_DIR, "db", "new_db.db")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("Uploader started...\n")

# ---------------- ENSURE uploaded COLUMN EXISTS ----------------
cur.execute("PRAGMA table_info(brake_pressure_log)")
columns = [col[1] for col in cur.fetchall()]

if "uploaded" not in columns:
    print("Adding 'uploaded' column...")
    cur.execute("ALTER TABLE brake_pressure_log ADD COLUMN uploaded INTEGER DEFAULT 0")
    conn.commit()

# ---------------- MAIN LOOP ----------------
while True:

    cur.execute("""
        SELECT * FROM brake_pressure_log
        WHERE uploaded = 0 OR uploaded IS NULL
        ORDER BY timestamp ASC
        LIMIT 1
    """)

    row = cur.fetchone()

    if row:
        try:
            payload = {
                "device_id": DEVICE_ID,
                "timestamp": row["timestamp"],
                "bp": int(row["BP_raw"]),
                "bc": int(row["BC_raw"]),
                "fp": int(row["FP_raw"]),
                "cr": int(row["CR_raw"])
            }

            print("📤 Sending Data:")
            print(f"Device_id      = {DEVICE_ID}")
            print(f"Timestamp      = {row['timestamp']}")
            print(f"BP_raw         = {row['BP_raw']}")
            print(f"BC_raw         = {row['BC_raw']}")
            print(f"FP_raw         = {row['FP_raw']}")
            print(f"CR_raw         = {row['CR_raw']}")

            mqtt_client.publish(TOPIC, json.dumps(payload), 1)

            cur.execute(
                "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                (row["id"],)
            )
            conn.commit()

            print("Uploaded Status = uploaded")
            print("--------------------------------------------------\n")

        except Exception as e:
            print("Publish Error:", e)

    else:
        print("No data to upload\n")

    time.sleep(2)