import ssl
import time
import json
import sys
import os
import paho.mqtt.client as mqtt

# ---------------- ENCODING SETUP ----------------
sys.stdout.reconfigure(encoding='utf-8')

# ---------------- BASE PATH ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ---------------- AWS IOT DETAILS ----------------
AWS_ENDPOINT = "amu2pa1jg3r4s-ats.iot.ap-south-1.amazonaws.com"
AWS_PORT = 8883
CLIENT_ID = "Raspberry_pi"
TOPIC = "raspi/pressure/data"

# ---------------- CERTIFICATE PATHS ----------------
CERT_DIR = os.path.join(BASE_DIR, "raspi")

CA_FILE = os.path.join(CERT_DIR, "AmazonRootCA1.pem")
CERT_FILE = os.path.join(
    CERT_DIR,
    "0a0f7d38323fdef876a81f1a8d6671502e80d50d6e2fdc753a68baa51cfcf5ef-certificate.pem.crt"
)
KEY_FILE = os.path.join(
    CERT_DIR,
    "0a0f7d38323fdef876a81f1a8d6671502e80d50d6e2fdc753a68baa51cfcf5ef-private.pem.key"
)

# ---------------- FILE CHECK ----------------
for f in [CA_FILE, CERT_FILE, KEY_FILE]:
    if not os.path.exists(f):
        print(f"❌ Missing file: {f}")
        sys.exit(1)

print("✅ All certificate files found")

# ---------------- MQTT CALLBACKS ----------------
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to AWS IoT Core")
    else:
        print("❌ Connection failed. RC:", rc)

def on_publish(client, userdata, mid):
    print("📤 Message published")

def on_disconnect(client, userdata, rc):
    print("🔌 Disconnected")

# ---------------- MQTT CLIENT SETUP ----------------
client = mqtt.Client(client_id=CLIENT_ID, protocol=mqtt.MQTTv311)

client.on_connect = on_connect
client.on_publish = on_publish
client.on_disconnect = on_disconnect

client.tls_set(
    ca_certs=CA_FILE,
    certfile=CERT_FILE,
    keyfile=KEY_FILE,
    tls_version=ssl.PROTOCOL_TLS_CLIENT
)

client.tls_insecure_set(False)

# ---------------- CONNECT ----------------
print("🔄 Connecting to AWS IoT...")
client.connect(AWS_ENDPOINT, AWS_PORT, keepalive=60)
client.loop_start()

# ---------------- PUBLISH LOOP ----------------
try:
    while True:
        payload = {
            "device": "Raspberry_pi",
            "pressure": 12.5,
            "unit": "bar",
            "timestamp": int(time.time())
        }

        client.publish(TOPIC, json.dumps(payload), qos=1)
        time.sleep(5)

except KeyboardInterrupt:
    print("\n⛔ Program stopped by user")

finally:
    client.loop_stop()
    client.disconnect()
