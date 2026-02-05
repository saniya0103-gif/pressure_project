import time
import sys
import sqlite3

# ---------------- ENCODING ----------------
sys.stdout.reconfigure(encoding='utf-8')

# ---------------- CONFIG ----------------
RAW_THRESHOLD = 1638              # ~0.5 bar
SENSOR_ID = "RPI_BP_01"
DB_PATH = "pressure_data.db"
READ_INTERVAL = 10                # seconds

# ---------------- DATABASE ----------------
conn = sqlite3.connect(DB_PATH, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS pressure_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sensor_id TEXT,
    bp_raw INTEGER,
    fp_raw INTEGER,
    cr_raw INTEGER,
    bc_raw INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

# ---------------- ADS1115 ----------------
ADS_AVAILABLE = True

try:
    import board
    import busio
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn

    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    ads.gain = 1

    bp_channel = AnalogIn(ads, 0)
    fp_channel = AnalogIn(ads, 1)
    cr_channel = AnalogIn(ads, 2)
    bc_channel = AnalogIn(ads, 3)

except Exception:
    ADS_AVAILABLE = False

# ---------------- SENSOR READ ----------------
def read_raw_values():
    if ADS_AVAILABLE:
        return (
            bp_channel.value,
            fp_channel.value,
            cr_channel.value,
            bc_channel.value
        )
    return (0, 0, 0, 0)

# ---------------- MAIN LOOP ----------------
print("System started...\n", flush=True)

last_raw = None

while True:
    current_raw = read_raw_values()
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')

    # ---- PRINT SENSOR VALUES ----
    print(
        "RAW SENSOR VALUES\n"
        f"ID: {SENSOR_ID}\n"
        f"BP: {current_raw[0]} | FP: {current_raw[1]} | "
        f"CR: {current_raw[2]} | BC: {current_raw[3]}\n"
        f"Time: {timestamp}",
        flush=True
    )

    # ---- FIRST ENTRY ----
    if last_raw is None:
        cursor.execute("""
            INSERT INTO pressure_log
            (sensor_id, bp_raw, fp_raw, cr_raw, bc_raw)
            VALUES (?, ?, ?, ?, ?)
        """, (SENSOR_ID, *current_raw))
        conn.commit()
        last_raw = current_raw

    else:
        diffs = [
            abs(current_raw[i] - last_raw[i]) for i in range(4)
        ]

        # ---- UPLOAD ONLY IF ANY SENSOR CROSSES THRESHOLD ----
        if any(diff >= RAW_THRESHOLD for diff in diffs):
            cursor.execute("""
                INSERT INTO pressure_log
                (sensor_id, bp_raw, fp_raw, cr_raw, bc_raw)
                VALUES (?, ?, ?, ?, ?)
            """, (SENSOR_ID, *current_raw))
            conn.commit()
            last_raw = current_raw
        else:
            print("⏭ No change raw value → Skipped upload", flush=True)

    print("---------------------------------------------\n", flush=True)
    time.sleep(READ_INTERVAL)
