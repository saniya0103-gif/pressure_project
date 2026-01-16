import sqlite3
import time
import sys

# ---------------- ENCODING SETUP ----------------
sys.stdout.reconfigure(encoding='utf-8')

DB_PATH = "/app/db/project.db"

# ---------------- DATABASE SETUP ----------------
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS brake_pressure_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bp_pressure REAL,
    fp_pressure REAL,
    cr_pressure REAL,
    bc_pressure REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    uploaded INTEGER DEFAULT 0
)
""")
conn.commit()

# ---------------- ADS1115 SETUP ----------------
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
    bc_channel = AnalogIn(ads, P3)

except Exception:
    ADS_AVAILABLE = False

# ---------------- SENSOR FUNCTIONS 
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

def convert_to_pressure(raw):
    # Convert raw ADC value to pressure (0–10 bar example)
    return round((raw / 32767) * 10, 2)

def get_pressures():
    raw = read_raw_values()
    pressures = tuple(convert_to_pressure(r) for r in raw)
    return raw, pressures

# ---------------- MAIN LOOP ----------------
print("\nSystem started... Logging data every 20 seconds\n")

while True:
    raw_values, pressures = get_pressures()

    cursor.execute("""
        SELECT bp_pressure, fp_pressure, cr_pressure, bc_pressure
        FROM brake_pressure_log
        ORDER BY id DESC
        LIMIT 1
    """)
    last = cursor.fetchone()

    if not last or any(abs(n - l) >= 0.5 for n, l in zip(pressures, last)):
        cursor.execute("""
            INSERT INTO brake_pressure_log
            (bp_pressure, fp_pressure, cr_pressure, bc_pressure)
            VALUES (?, ?, ?, ?)
        """, pressures)
        conn.commit()

    # Only print RAW and PRESSURE values
    print(
        f"RAW VALUES\n"
        f"BP:{raw_values[0]} | FP:{raw_values[1]} | "
        f"CR:{raw_values[2]} | BC:{raw_values[3]}\n"
        f"PRESSURE VALUES\n"
        f"BP:{pressures[0]} bar | FP:{pressures[1]} bar | "
        f"CR:{pressures[2]} bar | BC:{pressures[3]} bar\n"
        f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        "---------------------------------------------",
        flush=True
    )

    time.sleep(20)
