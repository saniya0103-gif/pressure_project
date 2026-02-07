import sqlite3
import time
import json
import ssl
import os
import paho.mqtt.client as mqtt
import signal
import sys

# ---------------- DYNAMIC PATH ----------------
BASE_PATH = "/app" if os.path.exists("/app") else os.path.dirname(os.path.abspath(__file__))
RASPI_PATH = os.path.join(BASE_PATH, "raspi")
DB_PATH    = os.path.join(BASE_PATH, "db", "project.db")

# ---------------- CERTIFICATE PATHS ----------------
paths = {
    "DB": DB_PATH,
    "CA": os.path.join(RASPI_PATH, "AmazonRootCA1 (4).pem"),
    "CERT": os.path.join(RASPI_PATH, "3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-certificate.pem.crt"),
    "KEY": os.path.join(RASPI_PATH, "3e866ef4c18b7534f9052110a7eb36cdede25434a3cc08e3df2305a14aba5175-private.pem.key")
}

# ---------------- MQTT CONFIG ----------------
ENDPOINT  = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
PORT      = 8883
CLIENT_ID = "Raspberry_pi"  # Must match AWS IoT policy
TOPIC     = "brake/pressure"

mqtt_client = None
connected_flag = False

# ---------------- CALLBACKS ----------------
def on_connect(client, userdata, flags, rc, properties=None):
    global connected_flag
    if rc == 0:
        print("✅ Connected to AWS IoT Core")
        connected_flag = True
    else:
        print("❌ MQTT connection failed, RC =", rc)
        connected_flag = False

def on_disconnect(client, userdata, rc):
    global connected_flag
    print("⚠ MQTT disconnected, RC:", rc)
    connected_flag = False

def on_publish(client, userdata, mid):
    print("Data published ---> mid:", mid)

# ---------------- MQTT CONNECT ----------------
def connect_mqtt():
    global mqtt_client
    mqtt_client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)
    mqtt_client.tls_set(
        ca_certs=paths["CA"],
        certfile=paths["CERT"],
        keyfile=paths["KEY"],
        tls_version=ssl.PROTOCOL_TLSv1_2
    )
    mqtt_client.on_connect = on_connect
    mqtt_client.on_disconnect = on_disconnect
    mqtt_client.on_publish = on_publish

    while True:
        try:
            mqtt_client.connect(ENDPOINT, PORT, keepalive=60)
            mqtt_client.loop_start()
            # Wait for connection
            timeout = 0
            while not connected_flag and timeout < 30:
                time.sleep(1)
                timeout += 1
            if connected_flag:
                break
            else:
                print("⚠ MQTT not connected, retrying...")
        except Exception as e:
            print("🔌 MQTT connection error:", e)
            time.sleep(5)

# ---------------- DATABASE ----------------
os.makedirs(os.path.dirname(paths["DB"]), exist_ok=True)
conn = sqlite3.connect(paths["DB"])
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# ---------------- UPLOAD FUNCTION ----------------
def upload_to_aws(row):
    if not connected_flag:
        print("⚠ MQTT not connected. Skipping publish.")
        return False

    payload = {
        "created_at": row["created_at"],
        "bp_pressure": row["bp_pressure"],
        "fp_pressure": row["fp_pressure"],
        "cr_pressure": row["cr_pressure"],
        "bc_pressure": row["bc_pressure"],
        "db_uploaded": row["uploaded"],
        "aws_status": "uploaded"
    }

    try:
        result = mqtt_client.publish(TOPIC, json.dumps(payload), qos=1)
        if result.rc == mqtt.MQTT_ERR_SUCCESS:
            print(f"➡️ Uploaded | id={row['id']} | BP={row['bp_pressure']} | FP={row['fp_pressure']} | CR={row['cr_pressure']} | BC={row['bc_pressure']}")
            return True
        else:
            print("❌ Publish failed, RC:", result.rc)
            return False
    except Exception as e:
        print("❌ Exception while publishing:", e)
        return False

# ---------------- MAIN LOOP ----------------
def main_loop():
    while True:
        try:
            cursor.execute("SELECT * FROM brake_pressure_log WHERE uploaded=0 ORDER BY created_at ASC")
            rows = cursor.fetchall()
            if not rows:
                time.sleep(5)
                continue

            for row in rows:
                success = upload_to_aws(row)
                if not success:
                    print("⚠ Upload failed, will retry later.")
                    break

                cursor.execute("UPDATE brake_pressure_log SET uploaded=1 WHERE id=?", (row["id"],))
                conn.commit()
                time.sleep(1)

        except Exception as e:
            print("❌ Main loop exception:", e)
            time.sleep(5)

# ---------------- GRACEFUL SHUTDOWN ----------------
def shutdown(sig, frame):
    print("🛑 Graceful shutdown")
    try:
        if mqtt_client:
            mqtt_client.loop_stop()
            mqtt_client.disconnect()
        conn.close()
    except:
        pass
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown)
signal.signal(signal.SIGTERM, shutdown)

# ---------------- START ----------------
connect_mqtt()
main_loop()
