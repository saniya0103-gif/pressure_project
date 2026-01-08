import paho.mqtt.client as mqtt
import json
import time

MQTT_BROKER = "398e8a90820d4da69bf78b8ace2a81b4.s1.eu.hivemq.cloud"
MQTT_PORT = 8883
MQTT_TOPIC = "test/pressure"

# Use callback_api_version=1 to fix ValueError
client = mqtt.Client(client_id="pi_test", callback_api_version=1)
client.username_pw_set("Saniya_p", "Saniya@9786")
client.tls_set()  # TLS for port 8883

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Connected successfully!")
    else:
        print("Connection failed, code:", rc)

client.on_connect = on_connect

client.connect(MQTT_BROKER, MQTT_PORT)
client.loop_start()

# Publish some test messages
for i in range(3):
    data = {"pressure_value": i}
    client.publish(MQTT_TOPIC, json.dumps(data))
    print("Sent:", data)
    time.sleep(2)
