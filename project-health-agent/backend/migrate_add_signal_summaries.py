import sqlite3

conn = sqlite3.connect('project_health.db')
try:
    conn.execute("ALTER TABLE weekly_snapshots ADD COLUMN signal_summaries TEXT DEFAULT '{}'")
    conn.commit()
    print("Column 'signal_summaries' added successfully")
except sqlite3.OperationalError as e:
    if "duplicate column name" in str(e):
        print("Column 'signal_summaries' already exists")
    else:
        raise
conn.close()
