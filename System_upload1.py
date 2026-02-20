import sqlite3
import time
import os
import json
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# ==============================
# DEVICE CONFIGURATION
# ==============================
DEVICE_ID = "Raspberry4_1"
ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"  # 🔴 Replace with your AWS IoT endpoint
PORT = 8883
TOPIC = "brake/data"

# ==============================
# PATH CONFIGURATION
# ==============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CERT_FOLDER = os.path.join(BASE_DIR, "certs")
DB_PATH = os.path.join(BASE_DIR, "db", "new_db.db")

ROOT_CA = os.path.join(CERT_FOLDER, "AmazonRootCA1.pem")
CERTIFICATE = os.path.join(CERT_FOLDER, "certificate.pem.crt")
PRIVATE_KEY = os.path.join(CERT_FOLDER, "private.pem.key")

# ==============================
# VERIFY CERTIFICATES
# ==============================
print("\n🔎 Verifying certificate files...")

for file_path in [ROOT_CA, CERTIFICATE, PRIVATE_KEY]:
    if not os.path.exists(file_path):
        print(f"❌ Missing file: {file_path}")
        exit()
    else:
        print(f"✅ Found: {file_path}")

print("🔐 Certificate verification successful!\n")

# ==============================
# DATABASE CONNECTION
# ==============================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

# Ensure uploaded column exists
cur.execute("PRAGMA table_info(brake_pressure_log)")
columns = [col[1] for col in cur.fetchall()]

if "uploaded" not in columns:
    print("➕ Adding 'uploaded' column...")
    cur.execute("ALTER TABLE brake_pressure_log ADD COLUMN uploaded INTEGER DEFAULT 0")
    conn.commit()

print("🚀 Uploader Started...\n")

# ==============================
# MQTT CLIENT SETUP
# ==============================
mqtt_client = AWSIoTMQTTClient(DEVICE_ID)
mqtt_client.configureEndpoint(ENDPOINT, PORT)
mqtt_client.configureCredentials(ROOT_CA, PRIVATE_KEY, CERTIFICATE)

mqtt_client.configureOfflinePublishQueueing(-1)
mqtt_client.configureDrainingFrequency(2)
mqtt_client.configureConnectDisconnectTimeout(10)
mqtt_client.configureMQTTOperationTimeout(5)

# MQTT status callbacks
mqtt_client.onOnline = lambda: print("🟢 MQTT Connected to AWS IoT Core")
mqtt_client.onOffline = lambda: print("🔴 MQTT Disconnected from AWS IoT Core")

print("🔌 Connecting to AWS IoT Core...\n")
mqtt_client.connect()

# ==============================
# MAIN LOOP
# ==============================
while True:
    cur.execute("""
        SELECT * FROM brake_pressure_log
        WHERE uploaded = 0 OR uploaded IS NULL
        ORDER BY timestamp ASC
        LIMIT 1
    """)

    row = cur.fetchone()

    if row:
        payload = {
            "Device_id": DEVICE_ID,
            "timestamp": row["timestamp"],
            "bp_raw": row["BP_raw"],
            "bc_raw": row["BC_raw"],
            "cr_raw": row["CR_raw"],
            "fp_raw": row["FP_raw"]
        }

        try:
            mqtt_client.publish(TOPIC, json.dumps(payload), 1)

            print("\n📤 Data Published to AWS IoT Core")
            print(f"Device_id  = {DEVICE_ID}")
            print(f"timestamp  = {row['timestamp']}")
            print(f"bp_raw     = {row['BP_raw']}")
            print(f"bc_raw     = {row['BC_raw']}")
            print(f"cr_raw     = {row['CR_raw']}")
            print(f"fp_raw     = {row['FP_raw']}")
            print("uploaded status: uploaded ✅")

            cur.execute(
                "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                (row["id"],)
            )
            conn.commit()

        except Exception as e:
            print("❌ Publish Failed:", e)

    else:
        print("⏳ No new data to upload...")

    time.sleep(2)