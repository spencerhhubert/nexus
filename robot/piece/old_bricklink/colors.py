import os
import requests
import sqlite3 as sql
from bricklink_auth import oauth


def updateColorsTable(db_path: str):
    base = "https://api.bricklink.com/api/store/v1"
    path = "/colors"
    response = requests.get(base + path, auth=oauth)
    response = response.json()["data"]
    print(f"found {len(response)} colors")

    # example entry
    # {'color_id': 219, 'color_name': 'Mx Foil Orange', 'color_code': 'F7AD63', 'color_type': 'Modulex'}

    # don't care about other types of colors like transparent and modulex for now
    colors = list(filter(lambda x: x["color_type"] == "Solid", response))

    conn = sql.connect(db_path)
    c = conn.cursor()
    c.execute(
        "CREATE TABLE IF NOT EXISTS colors (id TEXT PRIMARY KEY, name TEXT, code TEXT)"
    )
    c.executemany(
        "INSERT OR IGNORE INTO colors VALUES (?,?,?)",
        [(str(x["color_id"]), x["color_name"], x["color_code"]) for x in colors],
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    updateColorsTable("pieces.db")
