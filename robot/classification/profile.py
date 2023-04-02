import sqlite3 as sql
import json

def deserializeCategory(row:tuple) -> tuple:
    id = row[0]
    name = row[1]
    pieces = [] if row[2] == '' else json.loads(row[2])
    pieces = list(map(lambda x: (x[0], x[1]), pieces))
    kinds = [] if row[3] == '' else json.loads(row[3])
    colors = [] if row[4] == '' else json.loads(row[4])
    categories = row[5]
    return (id, name, pieces, kinds, colors, categories)

class Profile():
    def __init__(self, db_path:str):
        conn = sql.connect(db_path)
        c = conn.cursor()
        self.bins = c.execute("SELECT * FROM bricklink_categories_profile").fetchall()
        self.bins = list(map(deserializeCategory, self.bins))

    def belongsTo(self, piece:tuple) -> str:
        kind_id, color_id = piece
        for bin in self.bins:
            id = bin[0]
            kinds = bin[3]
            if kind_id in kinds:
                return id

    #from a list of predictions, which is the top that we actually have in our profile?
    def topExistentKind(self, kinds:list) -> str:
        for kind in kinds:
            for bin in self.bins:
                if kind in bin[3]:
                    return kind
        return None
