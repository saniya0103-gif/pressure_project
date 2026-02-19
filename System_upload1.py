import sqlite3
import time
import os

# ---------------- DATABASE PATH ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db", "new_db.db")

conn = sqlite3.connect(DB_PATH, check_same_thread=False)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

print("🚀 Uploader started...")

# ---------------- ENSURE uploaded COLUMN EXISTS ----------------
cur.execute("PRAGMA table_info(brake_pressure_log)")
columns = [col[1] for col in cur.fetchall()]

if "uploaded" not in columns:
    print("➕ Adding 'uploaded' column...")
    cur.execute("ALTER TABLE brake_pressure_log ADD COLUMN uploaded INTEGER DEFAULT 0")
    conn.commit()

# ---------------- UPLOAD FUNCTION ----------------
def upload_to_app(row):
    print(
        f"Uploading -> ID:{row['id']} "
        f"Time:{row['timestamp']} "
        f"BP:{row['BP_raw']} "
        f"BC:{row['BC_raw']} "
        f"FP:{row['FP_raw']} "
        f"CR:{row['CR_raw']}"
    )
    time.sleep(1)  # simulate upload delay
    return True

# ---------------- MAIN LOOP ----------------
while True:

    cur.execute("""
        SELECT * FROM brake_pressure_log
        WHERE uploaded = 0 OR uploaded IS NULL
        ORDER BY timestamp ASC
        LIMIT 1
    """)

    row = cur.fetchone()

    if row:
        if upload_to_app(row):
            cur.execute(
                "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                (row["id"],)
            )
            conn.commit()
            print(f"✅ Row {row['id']} marked uploaded (1)")
    else:
        print("⏳ No data to upload")

    time.sleep(2)
