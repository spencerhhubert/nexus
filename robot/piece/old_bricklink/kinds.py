import os
import requests
import json
from bricklink_auth import oauth
import sqlite3 as sql
from bs4 import BeautifulSoup
import argparse


def removeSpaceBeforeNumbers(s: str):
    s = list(s)
    for i, c in enumerate(s):
        if c.isdigit() and i > 0:
            s[i - 1] = ""
    return "".join(s)


def makeEmptyKindTable(db_path: str):
    conn = sql.connect(db_path)
    c = conn.cursor()

    c.execute(
        """
        CREATE TABLE kinds (
            id TEXT PRIMARY KEY,
            ml_id INTEGER,
            name TEXT,
            characteristics TEXT,
            alternate_ids TEXT
        );
    """
    )

    conn.commit()
    conn.close()


# get ldraw parts list from https://github.com/pybricks/ldraw/tree/master/mklist
def updateKindTable(db_path: str, ldraw_parts_list_path: str, replace: bool = False):
    conn = sql.connect(db_path)
    c = conn.cursor()

    # make the table if it doesn't exist
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS kinds (
            id TEXT PRIMARY KEY,
            ml_id INTEGER,
            name TEXT,
            characteristics TEXT,
            alternate_ids TEXT,
            dims TEXT
        );
    """
    )
    conn.commit()

    with open(ldraw_parts_list_path, "r") as f:
        for i, line in enumerate(f):
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
            bl_alternate_ids = part_info["alternate_no"].split(",")
            ids = list(set([ldraw_id] + [bl_primary_id] + bl_alternate_ids))
            alternate_ids = json.dumps(ids)

            name = part_info["name"]
            dims = json.dumps(
                list(
                    map(
                        float,
                        [part_info["dim_x"], part_info["dim_y"], part_info["dim_z"]],
                    )
                )
            )

            category = part_info["category_id"]
            category = getCategory(category)
            category = category["category_name"]
            characteristics = [category]
            characteristics = json.dumps(characteristics)

            cur_max_ml_id = c.execute("SELECT MAX(ml_id) FROM kinds").fetchone()[0]
            if cur_max_ml_id == None:
                cur_max_ml_id = 1
            ml_id = cur_max_ml_id + 1

            print(f"Inserting {name} into db")
            print(f"aka {line[1]}")

            if replace:
                c.execute(
                    """
                    INSERT OR REPLACE INTO kinds (id, ml_id, name, characteristics, alternate_ids, dims) VALUES (?, ?, ?, ?, ?, ?);
                """,
                    (bl_primary_id, ml_id, name, characteristics, alternate_ids, dims),
                )
            else:
                c.execute(
                    """
                    INSERT OR IGNORE INTO kinds (id, ml_id, name, characteristics, alternate_ids) VALUES (?, ?, ?, ?, ?, ?);
                """,
                    (bl_primary_id, ml_id, name, characteristics, alternate_ids, dims),
                )
            conn.commit()


def scrapePrimaryId(id: str) -> str:
    # given an alternate id, which many of the ids in ldraw are, you can't figure out the primary id from the bricklink api
    # and you need the primary id to get info about it from the bl api
    # so we gotta do this

    # get this curl info doing "copy cURL" from packet representing search page like https://www.bricklink.com/v2/search.page?q=72154 from the network tab of the browser
    # and use this https://curlconverter.com/
    # look for the searchproduct request

    cookies = {
        "l5_sp": "1eba0191-47c2-4aa3-96c7-a9b55b1155c4",
        "blckMID": "f270aba0-8394-460c-a837-126fd5288afe",
        "catalogView": "cView=1",
        "blCartBuyerID": "-707598233",
        "blckSessionStarted": "1",
        "blckCookieSetting": "CHKTGATFPBLF",
        "BLNEWSESSIONID": "V103226BBA237B88852C6B04CF2C7D73679A3D5FD03DCEE7BD80538EE86DB08044893ECDD768B92ECC96F4D7DC3E94A817A",
        "ASPSESSIONIDCAQASBCA": "GDNCHEODPIFAGFPIGJNDJPMN",
        "ASPSESSIONIDACSDRDCA": "GPBOAFODPIEODANGACAPHFFK",
        "BLdiscussFlag": "Y",
        "_pk_id.12.23af": "b2840f12a6d53d62.1749619769.",
        "ASPSESSIONIDAATCQCDA": "LLNOBNIAJLKFNKBMGHIEOBFM",
        "_pk_ses.12.23af": "1",
        "_sp_ses.8289": "*",
        "_sp_id.8289": ".1749493018.5.1749701832.1749624071.cf1a7e8e-1c65-4ff7-b761-a2ed8a413ffc..024c784e-e348-4b7b-90a2-5266cbac0c40.1749701808446.2",
        "aws-waf-token": "843b4532-05b0-494a-95ff-16ab8c6004eb:EQoAdoccqs/jAAAA:kzZL+rQ8o5yvRF/Rq7Sxw9QCIDj8TNG2PhA6mW772KkEboNW2qDfQacEBaHzGqmMezug1ikDP3wfex7GHQ/MfZ55vKIjmGuLaYQu/7i2EY2+C4adkBlkHgKyu6Yc3gt6nxPbp6oOnThZ97uh+HgdUPczvEHZcufiyYRiIsDbPaivGIm1wTnJGUVBfmQ7jZSHBjFAqVE1vQcLWKzBspqMfTSRM2hpgPuiVNF1nxUCcmhv+31jVRCWhZ+4LXvLKHlByD+KR5/Q8vU=",
        "AWSALB": "9TaJpQrjZUfTVZ6e4j4Qni7t6S7lscsGVUv8dhvpf/f5pbJ12qE9NxS4fphOdYx4ryXxHyJUPDAxlqc7MrcxSQitSDwOEQok4QJSSs0bhSlih1t5ELwKpeCPpGSz",
        "AWSALBCORS": "9TaJpQrjZUfTVZ6e4j4Qni7t6S7lscsGVUv8dhvpf/f5pbJ12qE9NxS4fphOdYx4ryXxHyJUPDAxlqc7MrcxSQitSDwOEQok4QJSSs0bhSlih1t5ELwKpeCPpGSz",
    }

    headers = {
        "accept": "application/json, text/javascript, */*; q=0.01",
        "accept-language": "en-US,en;q=0.9",
        "priority": "u=1, i",
        "referer": "https://www.bricklink.com/v2/search.page?q=72154",
        "sec-ch-ua": '"Brave";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"macOS"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "sec-gpc": "1",
        "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
        "x-requested-with": "XMLHttpRequest",
        # 'cookie': 'l5_sp=1eba0191-47c2-4aa3-96c7-a9b55b1155c4; blckMID=f270aba0-8394-460c-a837-126fd5288afe; catalogView=cView=1; blCartBuyerID=-707598233; blckSessionStarted=1; blckCookieSetting=CHKTGATFPBLF; BLNEWSESSIONID=V103226BBA237B88852C6B04CF2C7D73679A3D5FD03DCEE7BD80538EE86DB08044893ECDD768B92ECC96F4D7DC3E94A817A; ASPSESSIONIDCAQASBCA=GDNCHEODPIFAGFPIGJNDJPMN; ASPSESSIONIDACSDRDCA=GPBOAFODPIEODANGACAPHFFK; BLdiscussFlag=Y; _pk_id.12.23af=b2840f12a6d53d62.1749619769.; ASPSESSIONIDAATCQCDA=LLNOBNIAJLKFNKBMGHIEOBFM; _pk_ses.12.23af=1; _sp_ses.8289=*; _sp_id.8289=.1749493018.5.1749701832.1749624071.cf1a7e8e-1c65-4ff7-b761-a2ed8a413ffc..024c784e-e348-4b7b-90a2-5266cbac0c40.1749701808446.2; aws-waf-token=843b4532-05b0-494a-95ff-16ab8c6004eb:EQoAdoccqs/jAAAA:kzZL+rQ8o5yvRF/Rq7Sxw9QCIDj8TNG2PhA6mW772KkEboNW2qDfQacEBaHzGqmMezug1ikDP3wfex7GHQ/MfZ55vKIjmGuLaYQu/7i2EY2+C4adkBlkHgKyu6Yc3gt6nxPbp6oOnThZ97uh+HgdUPczvEHZcufiyYRiIsDbPaivGIm1wTnJGUVBfmQ7jZSHBjFAqVE1vQcLWKzBspqMfTSRM2hpgPuiVNF1nxUCcmhv+31jVRCWhZ+4LXvLKHlByD+KR5/Q8vU=; AWSALB=9TaJpQrjZUfTVZ6e4j4Qni7t6S7lscsGVUv8dhvpf/f5pbJ12qE9NxS4fphOdYx4ryXxHyJUPDAxlqc7MrcxSQitSDwOEQok4QJSSs0bhSlih1t5ELwKpeCPpGSz; AWSALBCORS=9TaJpQrjZUfTVZ6e4j4Qni7t6S7lscsGVUv8dhvpf/f5pbJ12qE9NxS4fphOdYx4ryXxHyJUPDAxlqc7MrcxSQitSDwOEQok4QJSSs0bhSlih1t5ELwKpeCPpGSz',
    }

    base = "https://www.bricklink.com"
    path = f"/ajax/clone/search/searchproduct.ajax?q={id}&st=0&cond=&type=&cat=&yf=0&yt=0&loc=&reg=0&ca=0&ss=&pmt=&nmp=0&color=-1&min=0&max=0&minqty=0&nosuperlot=1&incomplete=0&showempty=1&rpp=25&pi=1&ci=0"

    response = requests.get(base + path, cookies=cookies, headers=headers)
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
        part_info = getBLPartInfo(
            bl_primary_id
        )  # additional api call being made here that isn't totally necessary, TODO refactor to like cache or something
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


def getBLPartInfo(id: str):
    base = "https://api.bricklink.com/api/store/v1"
    path = f"/items/part/{id}"
    res = requests.get(base + path, auth=oauth)
    out = res.json()
    if "data" not in out:
        out["data"] = None
    return out["data"]


def getCategory(id: str):
    base_url = "https://api.bricklink.com/api/store/v1"
    url = base_url + f"/categories/{id}"
    response = requests.get(url, auth=oauth)
    return response.json()["data"]


def justUpdateDims(db_path: str, rate_limit: int = 4750):
    conn = sql.connect(db_path)
    c = conn.cursor()
    c.execute("SELECT * FROM kinds;")
    kinds = c.fetchall()
    num_reqs = 0
    for i, kind in enumerate(kinds):
        bl_id = kind[0]
        dims = kind[5]
        alt_ids = json.loads(kind[3])
        if dims == None:
            data = getBLPartInfo(bl_id)
            if data == None:
                altDatas = [getBLPartInfo(id) for id in alt_ids]
                for altData in altDatas:
                    if altData != None:
                        data = altData
                        break
                    continue
            dims = json.dumps(
                list(map(float, [data["dim_x"], data["dim_y"], data["dim_z"]]))
            )
            c.execute("UPDATE kinds SET dims = ? WHERE id = ?", (dims, bl_id))
            print(f"Updated dims for {bl_id}")
            conn.commit()
            num_reqs += 1
            if num_reqs > rate_limit:
                print("Rate limit reached. Exiting")
                break
        else:
            print(f"Skipping {bl_id}")
    conn.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--justDims", action="store_true")
    args = parser.parse_args()

    if args.justDims:
        justUpdateDims("pieces.db")
        exit()

    db_path = "pieces.db"
    ldraw_parts_list_path = "/home/spencer/code/ldraw/mklist/parts.lst"
    updateKindTable(db_path, ldraw_parts_list_path, replace=True)
