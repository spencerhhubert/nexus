import os
import requests
import json
from bricklink_auth import oauth
import sqlite3 as sql
from bs4 import BeautifulSoup

def removeSpaceBeforeNumbers(s:str):
    s = list(s)
    for i,c in enumerate(s):
        if c.isdigit() and i > 0:
            s[i-1] = ''
    return ''.join(s)

def makeEmptyKindTable(db_path:str):
    conn = sql.connect(db_path)
    c = conn.cursor()

    c.execute("""
        CREATE TABLE kinds (
            id TEXT PRIMARY KEY,
            ml_id INTEGER,
            name TEXT,
            characteristics TEXT,
            alternate_ids TEXT
        );
    """)

    conn.commit()
    conn.close()

#get ldraw parts list from https://github.com/pybricks/ldraw/tree/master/mklist
def updateKindTable(db_path:str, ldraw_parts_list_path:str, replace:bool=False):
    conn = sql.connect(db_path)
    c = conn.cursor()

    #make the table if it doesn't exist
    c.execute("""
        CREATE TABLE IF NOT EXISTS kinds (
            id TEXT PRIMARY KEY,
            ml_id INTEGER,
            name TEXT,
            characteristics TEXT,
            alternate_ids TEXT
        );
    """)
    conn.commit()

    with open(ldraw_parts_list_path, 'r') as f:
        for i,line in enumerate(f):
            line = line.split(".dat")
            ldraw_id = line[0].strip()

            bl_primary_id = scrapePrimaryId(ldraw_id)
            if bl_primary_id == None or bl_primary_id == "":
                continue

            if not replace:
                c.execute("SELECT * FROM kinds WHERE id=?", (bl_primary_id,))
                if c.fetchone() != None:
                    print(f"part {bl_primary_id} already in db. skipping")
                    continue

            part_info = getBLPartInfo(bl_primary_id)
            if "alternate_no" not in part_info:
                part_info["alternate_no"] = ""
            bl_alternate_ids = part_info["alternate_no"].split(',')
            ids = list(set([ldraw_id] + [bl_primary_id] + bl_alternate_ids))
            alternate_ids = json.dumps(ids)

            name = part_info["name"]

            category = part_info["category_id"]
            category = getCategory(category)
            category = category["category_name"]
            characteristics = [category]
            characteristics = json.dumps(characteristics)

            cur_max_ml_id = c.execute("SELECT MAX(ml_id) FROM kinds").fetchone()[0]
            if cur_max_ml_id == None:
                cur_max_ml_id = 0
            ml_id = cur_max_ml_id + 1

            print(f"Inserting {name} into db")
            print(f"aka {line[1]}")

            if replace:
                c.execute("""
                    INSERT OR REPLACE INTO kinds (id, ml_id, name, characteristics, alternate_ids) VALUES (?, ?, ?, ?, ?);
                """, (bl_primary_id, ml_id, name, characteristics, alternate_ids))
            else:
                c.execute("""
                    INSERT OR IGNORE INTO kinds (id, ml_id, name, characteristics, alternate_ids) VALUES (?, ?, ?, ?, ?);
                """, (bl_primary_id, ml_id, name, characteristics, alternate_ids))
            conn.commit()

def scrapePrimaryId(id:str) -> str:
    #given an alternate id, which many of the ids in ldraw are, you can't figure out the primary id from the bricklink api
    #and you need the primary id to get info about it from the bl api
    #so we gotta do this

    #get this curl info doing "copy cURL" from packet representing search page like https://www.bricklink.com/v2/search.page?q=72154 from the network tab of the browser
    #and use this https://curlconverter.com/

    cookies = {
        'blckMID': 'bfc2d42a-8792-470e-befd-9f27194d338c',
        'cartBuyerID': '-1477053304',
        'blckSessionStarted': '1',
        'BLNEWSESSIONID': 'V10DC861CB17DAB24ACC9DE250FD955C5B728BEDE3709FB19CE1834122EB57BE2238BB8115A70D3E969AB0FB2242318078B',
        'ASPSESSIONIDQSBTQSQD': 'PGFNLAEBGMNBBFKANOHMKKJF',
        'ASPSESSIONIDSSDTQTRD': 'KBNMJAEBDEGHCBHHFKMDNPCM',
        'AWSALB': 'Oof3WiXYzOap/Kc7YT4acUYYIFoGC13Y3sFpHZxQBv5snYGco0JAvJlKbBtxpeB9TSQ3NJfKDjr6hwPT7M9Q95oKoW7fVm5xbwmet6Saocdr95unuiEn/vREIE8O',
        'AWSALBCORS': 'Oof3WiXYzOap/Kc7YT4acUYYIFoGC13Y3sFpHZxQBv5snYGco0JAvJlKbBtxpeB9TSQ3NJfKDjr6hwPT7M9Q95oKoW7fVm5xbwmet6Saocdr95unuiEn/vREIE8O',
    }

    headers = {
        'authority': 'www.bricklink.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.5',
        'cache-control': 'max-age=0',
        # 'cookie': 'blckMID=bfc2d42a-8792-470e-befd-9f27194d338c; cartBuyerID=-1477053304; blckSessionStarted=1; BLNEWSESSIONID=V10DC861CB17DAB24ACC9DE250FD955C5B728BEDE3709FB19CE1834122EB57BE2238BB8115A70D3E969AB0FB2242318078B; ASPSESSIONIDQSBTQSQD=PGFNLAEBGMNBBFKANOHMKKJF; ASPSESSIONIDSSDTQTRD=KBNMJAEBDEGHCBHHFKMDNPCM; AWSALB=Oof3WiXYzOap/Kc7YT4acUYYIFoGC13Y3sFpHZxQBv5snYGco0JAvJlKbBtxpeB9TSQ3NJfKDjr6hwPT7M9Q95oKoW7fVm5xbwmet6Saocdr95unuiEn/vREIE8O; AWSALBCORS=Oof3WiXYzOap/Kc7YT4acUYYIFoGC13Y3sFpHZxQBv5snYGco0JAvJlKbBtxpeB9TSQ3NJfKDjr6hwPT7M9Q95oKoW7fVm5xbwmet6Saocdr95unuiEn/vREIE8O',
        'referer': 'https://www.bricklink.com/catalogList.asp?catType=P&catString=437',
        'sec-ch-ua': '"Brave";v="111", "Not(A:Brand";v="8", "Chromium";v="111"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"macOS"',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'sec-gpc': '1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Safari/537.36',
    }

    base = "https://www.bricklink.com"
    path = f"/ajax/clone/search/searchproduct.ajax?q={id}&st=0&cond=&type=&cat=&yf=0&yt=0&loc=&reg=0&ca=0&ss=&pmt=&nmp=0&color=-1&min=0&max=0&minqty=0&nosuperlot=1&incomplete=0&showempty=1&rpp=25&pi=1&ci=0"

    response = requests.get(base+path, cookies=cookies, headers=headers)
    response = response.json()
    
    if not "result" in response:
        print(f"Failed to get results for {id}. Skipping")
        return None
    success = len(response["result"]["typeList"]) > 0
    if not success:
        print(f"No results for {id}. Skipping") 
        return None

    results = response["result"]["typeList"][0]["items"]
    
    for result in results:
        bl_primary_id = result["strItemNo"]
        part_info = getBLPartInfo(bl_primary_id) #additional api call being made here that isn't totally necessary, TODO refactor to like cache or something
        if "alternate_no" in part_info:
            alternate_ids = part_info["alternate_no"].split(",")
            if id in alternate_ids:
                print(f"Successfully found primary id {bl_primary_id} for {id}")
                return bl_primary_id

    if len(results) == 1 and "alternate_no" in getBLPartInfo(results[0]["strItemNo"]):
        print(f"No alternate ids for {id}")
        return bl_primary_id
    
    print(f"Default skip for {id}.")
    return None

def getBLPartInfo(id:str):
    base = "https://api.bricklink.com/api/store/v1"
    path = f"/items/part/{id}"
    response = requests.get(base+path, auth=oauth)
    return response.json()["data"]

def getCategory(id:str):
    base_url = "https://api.bricklink.com/api/store/v1"
    url = base_url + f"/categories/{id}"
    response = requests.get(url, auth=oauth)
    return response.json()["data"]

if __name__ == "__main__":
    db_path = "pieces.db"
    ldraw_parts_list_path = "/home/spencer/code/ldraw/mklist/parts.lst"
    updateKindTable(db_path, ldraw_parts_list_path, replace=True)
