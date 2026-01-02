# uplo.py
import sqlite3

# Windows path for PC or Linux path for Docker
DB_PATH = "project.db"  # database will be created in the same folder as thee.py

def upload_status():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Select rows that are not uploaded
    cursor.execute("SELECT * FROM brake_pressure_log WHERE uploaded=0")
    rows = cursor.fetchall()

    for row in rows:
        # row = id, bp, fp, cr, bc, created_at, uploaded
        print(
            f"Uploading -> ID:{row[0]} | BP:{row[1]} | FP:{row[2]} | CR:{row[3]} | BC:{row[4]} | "
            f"Time:{row[5]} | Uploaded:{row[6]}",
            flush=True
        )

        # Mark as uploaded
        cursor.execute("UPDATE brake_pressure_log SET uploaded=1 WHERE id=?", (row[0],))

    conn.commit()
    conn.close()
