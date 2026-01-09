import sqlite3
import time

DB_PATH = "project.db"   # mounted volume path inside container

time.sleep(10)  # wait for the database to be ready

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
cur = conn.cursor()

def upload_to_app(row):
    print(
        f"Uploading -> "
        f"ID:{row['id']} | "
        f"Time:{row['created_at']} | "
        f"BP:{row['bp']} | "
        f"BC:{row['bc']} | "
        f"CR:{row['cr']} | "
        f"FP:{row['fp']} | "
        f"Uploaded:{row['uploaded']}"
    )
    time.sleep(1)
    return True

while True:
    cur.execute("""
        SELECT * FROM brake_pressure_log
        WHERE uploaded = 0
        ORDER BY created_at ASC
        LIMIT 1
    """)
    row = cur.fetchone()

    if row:
        if upload_to_app(row):
            cur.execute(
                "UPDATE brake_pressure_log SET uploaded = 1 WHERE id = ?",
                (row['id'],)
            )
            conn.commit()
            print(f"Row {row['id']} marked uploaded (1)")
    else:
        print("No data to upload")

    time.sleep(10)