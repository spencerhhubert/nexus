import sqlite3 as sql
import json

if False:
    db_path = "pieces.db"
    conn = sql.connect(db_path)
    c = conn.cursor()

    c.execute("DROP TABLE IF EXISTS bricklink_categories_profile")
    conn.commit()
    c.execute("CREATE TABLE IF NOT EXISTS bricklink_categories_profile AS SELECT * FROM categories")
    conn.commit()
    conn.close()

#conduct a test. find what category kind "3001" belongs to
db_path = "pieces.db"
conn = sql.connect(db_path)
c = conn.cursor()

categories = c.execute("SELECT * FROM bricklink_categories_profile")
#this is horrible for efficiency but oh well such is sqlite
for category in categories.fetchall():
    kinds = json.loads(category[3])
    if "3001" in kinds:
        print(category)
        break
