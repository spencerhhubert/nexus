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
            name TEXT,
            characteristics TEXT,
            alterate_ids TEXT
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
            name TEXT,
            characteristics TEXT,
            alterate_ids TEXT
        );
    """)
    conn.commit()

    with open(ldraw_parts_list_path, 'r') as f:
        for i,line in enumerate(f):
            line = line.split('=')
            line[0] = line[0].strip()

            ldraw_id = line[0][:-4] #remove .dat

            c.execute("SELECT * FROM kinds WHERE id=?", (ldraw_id,))
            if c.fetchone() != None:
                print(f"part {ldraw_id} already in db. skipping")
                continue

            bl_primary_id = scrapePrimaryId(ldraw_id)
            if bl_primary_id == None or bl_primary_id == "":
                print(f"part {ldraw_id} not found on bricklink. skipping")
                continue

            part_info = getBLPartInfo(bl_primary_id)
            bl_alternate_ids = part_info["alternate_no"].split(',')
            ids = list(set([ldraw_id] + [bl_primary_id] + bl_alternate_ids))
            alterate_ids = json.dumps(ids)

            name = part_info["name"]

            category = part_info["category_id"]
            category = getCategory(category)
            category = category["category_name"]
            characteristics = [category]
            characteristics = json.dumps(characteristics)

            print(f"inserting {ldraw_id} {name} into {db_path}")

            if replace:
                c.execute("""
                    INSERT OR REPLACE INTO kinds (id, name, characteristics, alterate_ids) VALUES (?, ?, ?, ?);
                """, (ldraw_id, name, characteristics, alterate_ids))
            else:
                c.execute("""
                    INSERT OR IGNORE INTO kinds (id, name, characteristics, alterate_ids) VALUES (?, ?, ?, ?);
                """, (ldraw_id, name, characteristics, alterate_ids))
            conn.commit()

def scrapePrimaryId(id:str) -> str:
    #given an alternate id, which many of the ids in ldraw are, you can't figure out the primary id from the bricklink api
    #and you need the primary id to get info about it from the bl api
    #so we gotta do this

    #get this curl info doing "copy cURL" from packet representing search page like https://www.bricklink.com/v2/search.page?q=72154 from the network tab of the browser
    #and use this https://curlconverter.com/

    cookies = {
        'BLNEWSESSIONID': 'V108157EC42E8A967B04329C3A5D0FCDE2A93CB02FE6F21C87E6A888C2AE1FF0A42EC9B7C67A7414B0F716370A1276A3FA2',
        'cartBuyerID': '-1477601822',
        'blckMID': '18714c74c6500000-fbf5455ea27661db',
        'blckSessionStarted': '1',
        'blckCookieSetting': 'CHKTGATFPBLF',
        'AWSALB': 'UBbpEBYGYFtC8eRTpt9KzBCMtfd/n51R425GpOKqnIhapz096VxMJ+cCpKhNKYOk4LTvCRo1zyIl0BgqkPU7AXUhKxPBZf2jPe24T/KoDpSZ7MR0LCA+zQUjDSZL',
        'AWSALBCORS': 'UBbpEBYGYFtC8eRTpt9KzBCMtfd/n51R425GpOKqnIhapz096VxMJ+cCpKhNKYOk4LTvCRo1zyIl0BgqkPU7AXUhKxPBZf2jPe24T/KoDpSZ7MR0LCA+zQUjDSZL',
    }

    headers = {
        'authority': 'www.bricklink.com',
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'accept-language': 'en-US,en;q=0.5',
        # 'cookie': 'BLNEWSESSIONID=V108157EC42E8A967B04329C3A5D0FCDE2A93CB02FE6F21C87E6A888C2AE1FF0A42EC9B7C67A7414B0F716370A1276A3FA2; cartBuyerID=-1477601822; blckMID=18714c74c6500000-fbf5455ea27661db; blckSessionStarted=1; blckCookieSetting=CHKTGATFPBLF; AWSALB=UBbpEBYGYFtC8eRTpt9KzBCMtfd/n51R425GpOKqnIhapz096VxMJ+cCpKhNKYOk4LTvCRo1zyIl0BgqkPU7AXUhKxPBZf2jPe24T/KoDpSZ7MR0LCA+zQUjDSZL; AWSALBCORS=UBbpEBYGYFtC8eRTpt9KzBCMtfd/n51R425GpOKqnIhapz096VxMJ+cCpKhNKYOk4LTvCRo1zyIl0BgqkPU7AXUhKxPBZf2jPe24T/KoDpSZ7MR0LCA+zQUjDSZL',
        'sec-fetch-dest': 'document',
        'sec-fetch-mode': 'navigate',
        'sec-fetch-site': 'same-origin',
        'sec-fetch-user': '?1',
        'sec-gpc': '1',
        'upgrade-insecure-requests': '1',
        'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36',
    }

    base = "https://www.bricklink.com"
    path = f"/ajax/clone/search/searchproduct.ajax?q={id}&st=0&cond=&type=&cat=&yf=0&yt=0&loc=&reg=0&ca=0&ss=&pmt=&nmp=0&color=-1&min=0&max=0&minqty=0&nosuperlot=1&incomplete=0&showempty=1&rpp=25&pi=1&ci=0"

    response = requests.get(base+path, cookies=cookies, headers=headers)
    response = response.json()

    success = len(response["result"]["typeList"]) > 0
    if not success:
        return None

    for result in response["result"]["typeList"][0]["items"]:
        bl_primary_id = result["strItemNo"]
        part_info = getBLPartInfo(bl_primary_id) #additional api call being made here that isn't totally necessary, TODO refactor to like cache or something
        if not "alternate_no" in part_info:
            continue
        alternate_ids = part_info["alternate_no"].split(",")
        if not id in alternate_ids:
            continue
        return bl_primary_id

    return None

    id = response["result"]["typeList"][0]["items"][0]["strItemNo"]
    return id

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
    db_path = "parts_temp.db"
    ldraw_parts_list_path = "/home/spencer/code/ldraw/mklist/parts.lst"
    updateKindTable(db_path, ldraw_parts_list_path, replace=True)

