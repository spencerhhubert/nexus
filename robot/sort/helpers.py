import os
import json

def saveBuffer(buffer:list, out_dir:str, preds:dict=None):
    if preds is not None:
        os.makedirs(out_dir, exist_ok=True)
        preds_out_path = os.path.join(out_dir, "preds.json")
        with open(out_path, "w") as f:
            json.dump(preds, f)
    for i,img in enumerate(buffer):
        #save whole buffer to the same folder
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{i}.png")
        img = img.float()
        img = img / 255
        print(img.shape)
        img = img.unsqueeze(0)
        save_image(img, out_path)
    print("saved buffer")

incrementBins(dms:list, category:str) -> tuple:
    for dm in dms:
        for bin in dm.bins:
            if bin.category == category:
                return bin, dms
            if bin.category == None:
                bin.category = category
                return bin, dms
    print("out of bins, using last bin in last distribution module")
    return (dms[-1].bins[-1], dms)
