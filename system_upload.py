import sqlite3
import time
import json
import ssl
import os
import glob
import paho.mqtt.client as mqtt

# ---------------- DYNAMIC BASE PATH ----------------
BASE_PATH = "/app" if os.path.exists("/app") else os.path.dirname(os.path.abspath(__file__))

# ---------------- PATHS ----------------
AWS_PATH = os.path.join(BASE_PATH, "aws_iot")
DB_PATH  = os.path.join(BASE_PATH, "db", "project.db")

print("=== DEBUG START ===", flush=True)
print("BASE_PATH:", BASE_PATH, flush=True)
print("AWS_PATH:", AWS_PATH, flush=True)
print("DB_PATH:", DB_PATH, flush=True)

# Ensure AWS folder exists
if not os.path.exists(AWS_PATH):
    raise FileNotFoundError(f"AWS folder not found: {AWS_PATH}")

# Automatically detect cert and key files
CERT_FILES = glob.glob(os.path.join(AWS_PATH, "*-certificate.pem.crt"))
KEY_FILES  = glob.glob(os.path.join(AWS_PATH, "*-private.pem.key"))
CA_FILES   = glob.glob(os.path.join(AWS_PATH, "AmazonRootCA*.pem"))

if not CERT_FILES or not KEY_FILES or not CA_FILES:
    raise FileNotFoundError("AWS certificate/key/CA files missing in aws_iot folder.")

CERT_PATH = CERT_FILES[0]
KEY_PATH  = KEY_FILES[0]
CA_PATH   = CA_FILES[0]

print("Detected AWS files:")
print("CA_PATH:", CA_PATH)
print("CERT_PATH:", CERT_PATH)
print("KEY_PATH:", KEY_PATH)
print("=== DEBUG END ===", flush=True)

# ---------------- MQTT CONFIG ----------------
ENDPOINT  = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
PORT      = 8883
CLIENT_ID = "Raspberry"
TOPIC     = "brake/pressure"

# ---------------- CALLBACKS ----------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core")
    else:
        print("❌ MQTT connection failed, RC =", rc)

def on_publish(client, userdata, mid):
    print("Data published --->")

# ---------------- MQTT CONNECT ----------------
def connect_mqtt():
    print("Connecting to AWS IoT...")
    client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311, transport="tcp")
    client.on_connect = on_connect
    client.on_publish = on_publish

    # TLS config
    client.tls_set(
        ca_certs=CA_PATH,
        certfile=CERT_PATH,
        keyfile=KEY_PATH,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )

    client.connect(ENDPOINT, PORT, keepalive=60)
    client.loop_start()
    return client

# ---------------- WAIT FOR MQTT ----------------
mqtt_client = None
while mqtt_client is None:
    try:
        mqtt_client = connect_mqtt()
    except Exception as e:
        print("❌ MQTT connect error:", e)
        time.sleep(5)

# ---------------- DATABASE ----------------
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ---------------- UPLOAD FUNCTION ----------------
def upload_to_aws(row):
    payload = {
        "created_at": row["created_at"],
        "bp_pressure": row["bp_pressure"],
        "fp_pressure": row["fp_pressure"],
        "cr_pressure": row["cr_pressure"],
        "bc_pressure": row["bc_pressure"],
        "db_uploaded": row["uploaded"],
        "aws_status": "uploaded"
    }

    result = mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)

    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(
            f"➡️ Uploaded | id={row['id']} | "
            f"BP={row['bp_pressure']} bar | "
            f"FP={row['fp_pressure']} bar | "
            f"CR={row['cr_pressure']} bar | "
            f"BC={row['bc_pressure']} bar | "
            f"created_at={row['created_at']}"
        )
        return True
    else:
        print("❌ Publish failed:", result.rc)
        return False

# ---------------- MAIN LOOP ----------------
while True:
    cursor.execute("""
        SELECT * FROM brake_pressure_log
        WHERE uploaded = 0
        ORDER BY created_at ASC
    """)
    rows = cursor.fetchall()

    if not rows:
        print("No pending rows. Waiting...")
        time.sleep(5)
        continue

    for row in rows:
        success = upload_to_aws(row)
        if not success:
            print("Upload failed, will retry later.")
            break

        time.sleep(2)  # slight delay

        cursor.execute(
            "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
            (row["id"],)
        )
        conn.commit()

        print(
            f"✅ Marked uploaded | id={row['id']} | "
            f"BP={row['bp_pressure']} bar | "
            f"FP={row['fp_pressure']} bar | "
            f"CR={row['cr_pressure']} bar | "
            f"BC={row['bc_pressure']} bar | "
            f"created_at={row['created_at']}"
        )
