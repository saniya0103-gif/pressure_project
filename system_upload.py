import sqlite3
import time
import json
import ssl
import os
import gc
import paho.mqtt.client as mqtt

# =========================================================
# BASE PATH (works for docker + local)
# =========================================================
BASE_PATH = os.path.dirname(os.path.abspath(__file__))

# =========================================================
# PATHS
# =========================================================
RASPI_PATH = os.path.join(BASE_PATH, "raspi")
DB_PATH = os.path.join(BASE_PATH, "db", "project.db")

CA_PATH = os.path.join(RASPI_PATH, "AmazonRootCA1.pem")
CERT_PATH = os.path.join(
    RASPI_PATH,
    "0a0f7d38323fdef876a81f1a8d6671502e80d50d6e2fdc753a68baa51cfcf5ef-certificate.pem.crt"
)
KEY_PATH = os.path.join(
    RASPI_PATH,
    "0a0f7d38323fdef876a81f1a8d6671502e80d6e2fdc753a68baa51cfcf5ef-private.pem.key"
)

# =========================================================
# VERIFY FILES (FAIL FAST – NO SILENT ERRORS)
# =========================================================
for name, path in {
    "CA": CA_PATH,
    "CERT": CERT_PATH,
    "KEY": KEY_PATH,
    "DB": DB_PATH
}.items():
    if not os.path.exists(path):
        raise FileNotFoundError(f"{name} not found: {path}")

print("✅ All certificate & DB files found", flush=True)

# =========================================================
# AWS IOT CONFIG
# =========================================================
ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
PORT = 8883
CLIENT_ID = "Raspberry_pi"
TOPIC = "brake/pressure"

# =========================================================
# MQTT CALLBACKS
# =========================================================
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core", flush=True)
    else:
        print(f"❌ MQTT connect failed (rc={rc})", flush=True)

def on_publish(client, userdata, mid):
    print("📤 Message published", flush=True)

# =========================================================
# MQTT CONNECT
# =========================================================
def connect_mqtt():
    print("🔄 Connecting to AWS IoT...", flush=True)

    client = mqtt.Client(
        client_id=CLIENT_ID,
        protocol=mqtt.MQTTv311
    )

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

mqtt_client = None
while mqtt_client is None:
    try:
        mqtt_client = connect_mqtt()
    except Exception as e:
        print("❌ MQTT error:", e, flush=True)
        time.sleep(5)

# =========================================================
# DATABASE
# =========================================================
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# =========================================================
# UPLOAD FUNCTION
# =========================================================
def upload_to_aws(row):
    payload = {
        "id": row["id"],
        "timestamp": row["created_at"],
        "bp": row["bp_pressure"],
        "fp": row["fp_pressure"],
        "cr": row["cr_pressure"],
        "bc": row["bc_pressure"]
    }

    result = mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)

    if result.rc == mqtt.MQTT_ERR_SUCCESS:
        print(
            f"➡️ Uploaded | id={row['id']} | "
            f"BP={row['bp_pressure']} | "
            f"FP={row['fp_pressure']} | "
            f"CR={row['cr_pressure']} | "
            f"BC={row['bc_pressure']} | "
            f"time={row['created_at']}",
            flush=True
        )
        return True
    else:
        print("❌ Publish failed:", result.rc, flush=True)
        return False

# =========================================================
# MAIN LOOP (CONTINUOUS, SAFE, STABLE)
# =========================================================
while True:
    cursor.execute("""
        SELECT *
        FROM brake_pressure_log
        WHERE uploaded = 0
        ORDER BY created_at ASC
    """)
    rows = cursor.fetchall()

    if not rows:
        print("⏳ No pending rows. Waiting...", flush=True)
        gc.collect()
        time.sleep(10)
        continue

    for row in rows:
        if upload_to_aws(row):
            cursor.execute(
                "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                (row["id"],)
            )
            conn.commit()
            print(f"✅ Marked uploaded | id={row['id']}", flush=True)
        else:
            print("⚠️ Upload failed, retry later", flush=True)
            break

        gc.collect()
        time.sleep(10)
