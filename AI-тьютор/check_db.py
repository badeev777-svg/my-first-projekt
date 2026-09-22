import sqlite3

conn = sqlite3.connect('speakbuddy.db')
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
tables = cursor.fetchall()
print("Tables in speakbuddy.db:")
for t in tables:
    print(f"  - {t[0]}")

# Check user count
if tables and any(t[0] == 'user' for t in tables):
    cursor.execute("SELECT COUNT(*) FROM user")
    count = cursor.fetchone()[0]
    print(f"\nUsers in DB: {count}")

conn.close()
