import sqlite3 as sql

class Profile():
    def __init__(self, db_path:str):
        self.db_path = db_path
        self.db = sql.connect(self.db_path)
        self.cursor = self.db.cursor()

    def belongsTo(piece:tuple) -> str:
        kind_id, color_id = piece
        #return category id belonging to a piece
