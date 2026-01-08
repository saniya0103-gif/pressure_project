import paho.mqtt.client as mqtt

MQTT_BROKER = "398e8a90820d4da69bf78b8ace2a81b4.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_TOPIC = "test/pressure"

client = mqtt.Client("pi_test")
client.username_pw_set("YOUR_USERNAME", "YOUR_PASSWORD")
client.tls_set()  # Required for port 8883

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected successfully!")
    else:
        print("Connection failed, code:", rc)

client.on_connect = on_connect
client.connect(MQTT_BROKER, MQTT_PORT)
client.loop_start()

# Test publish
import time, json
for i in range(3):
    data = {"value": i}
    client.publish(MQTT_TOPIC, json.dumps(data))
    print("Sent:", data)
    time.sleep(2)
