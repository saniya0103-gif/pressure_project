import time
import sys

#ENCODING SETUP
sys.stdout.reconfigure(encoding='utf-8')

# ADS1115 SETUP 
ADS_AVAILABLE = True

try:
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn

    # Initialize I2C
    i2c = busio.I2C(board.SCL, board.SDA)

    # Initialize ADS1115
    ads = ADS.ADS1115(i2c)
    ads.gain = 1

    # ADS1115 Channels
    bp_channel = AnalogIn(ads, 0)
    fp_channel = AnalogIn(ads, 1)
    cr_channel = AnalogIn(ads, 2)
    bc_channel = AnalogIn(ads, 3)

    print("ADS1115 sensor detected and connected.\n", flush=True)

except Exception as e:
    print("⚠️ ADS1115 sensor not found. Using dummy zeros.", flush=True)
    ADS_AVAILABLE = False

#  SENSOR FUNCTIONS 
def read_raw_values():
    if ADS_AVAILABLE:
        return (
            bp_channel.value,
            fp_channel.value,
            cr_channel.value,
            bc_channel.value
        )
    else:
        return (0, 0, 0, 0)

# ---------------- MAIN LOOP ----------------
print("System started... Printing raw sensor data every 10 seconds\n", flush=True)

while True:
    raw_values = read_raw_values()

    print(
        f"RAW SENSOR VALUES\n"
        f"BP: {raw_values[0]} | FP: {raw_values[1]} | "
        f"CR: {raw_values[2]} | BC: {raw_values[3]}\n"
        f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        "---------------------------------------------",
        flush=True
    )

    time.sleep(10)
