from Adafruit_IO import MQTTClient

ADAFRUIT_IO_USERNAME = "your_username"
ADAFRUIT_IO_KEY = "your_aio_key"  # Get from Adafruit IO settings
FEED_ID = "brake_pressure"

def connected(client):
    print("Connected to Adafruit IO")

def disconnected(client):
    print("Disconnected from Adafruit IO")

client = MQTTClient(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)
client.on_connect = connected
client.on_disconnect = disconnected
client.connect()
client.loop_background()

# Send data
client.publish(FEED_ID, 5.4)
