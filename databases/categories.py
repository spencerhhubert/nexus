import sqlite3 as sql
import json

db_path = "pieces.db"
conn = sql.connect(db_path)
c = conn.cursor()

#drop table
c.execute('''DROP TABLE IF EXISTS categories''')
conn.commit()
c.execute('''CREATE TABLE IF NOT EXISTS categories (category TEXT PRIMARY KEY, name TEXT, pieces TEXT, kinds TEXT,colors TEXT, categories TEXT)''')

for kind in c.execute('''SELECT * FROM kinds''').fetchall():
    id = kind[0]
    characteristics = json.loads(kind[2])
    bl_category = characteristics[0]
    #see if bl_category exists
    c.execute('''SELECT * FROM categories WHERE category=?''', (bl_category,))
    category = c.fetchone()
    if category:
        kinds = json.loads(category[3])
        kinds.append(id)
        kinds = list(set(kinds))
        c.execute('''UPDATE categories SET kinds=? WHERE category=?''', (json.dumps(kinds), bl_category))
    else:
        c.execute('''INSERT INTO categories VALUES (?,?,?,?,?,?)''', (bl_category, bl_category, '', json.dumps([id]), '', ''))
    conn.commit()

for category in c.execute('''SELECT * FROM categories'''):
    print(category)

conn.close()

