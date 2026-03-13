from flask import Flask, request, jsonify, send_from_directory, render_template, redirect
import os
import json
import time
import uuid

app = Flask(__name__)

DB = "keys.json"
FILES = "keyfiles"

os.makedirs(FILES, exist_ok=True)

# ---------------------

def load():
    if not os.path.exists(DB):
        return {}
    with open(DB) as f:
        return json.load(f)

def save(data):
    with open(DB,"w") as f:
        json.dump(data,f,indent=4)

# ---------------------
# CLEAN KEYS
# ---------------------

def clean():

    db = load()
    now = time.time()

    changed = False

    for k in list(db.keys()):

        # xoá key hết hạn
        if now > db[k]["expire"]:
            del db[k]
            changed = True
            continue

        # reset device sau 24h
        if db[k]["device"] is not None:
            if now - db[k]["device_time"] > 86400:
                db[k]["device"] = None
                changed = True

    if changed:
        save(db)

# ---------------------
# PANEL
# ---------------------

@app.route("/")
def panel():

    clean()

    db = load()

    data = []

    for k,v in db.items():

        remain = max(0,int(v["expire"]-time.time()))

        days = remain//86400
        hours = (remain%86400)//3600

        data.append({
            "key":k,
            "days":days,
            "hours":hours
        })

    return render_template("panel.html",keys=data)

# ---------------------
# CREATE KEY
# ---------------------

@app.route("/create",methods=["POST"])
def create():

    db = load()

    days = int(request.form["days"])

    key = str(uuid.uuid4())[:8]

    expire = time.time() + days*86400

    db[key] = {
        "expire":expire,
        "device":None,
        "device_time":0
    }

    os.makedirs(f"{FILES}/{key}",exist_ok=True)

    save(db)

    return redirect("/")

# ---------------------
# EXTEND KEY
# ---------------------

@app.route("/extend/<key>/<int:days>")
def extend(key,days):

    db = load()

    if key in db:
        db[key]["expire"] += days*86400
        save(db)

    return redirect("/")

# ---------------------
# DELETE KEY
# ---------------------

@app.route("/delete/<key>")
def delete(key):

    db = load()

    if key in db:
        del db[key]
        save(db)

    return redirect("/")

# ---------------------
# UPLOAD FILE
# ---------------------

@app.route("/upload/<key>",methods=["POST"])
def upload(key):

    file = request.files["file"]

    path = f"{FILES}/{key}"

    os.makedirs(path,exist_ok=True)

    file.save(os.path.join(path,file.filename))

    return redirect("/")

# ---------------------
# CLIENT CHECK
# ---------------------

@app.route("/api/check",methods=["POST"])
def check():

    clean()

    key = request.json["key"]

    db = load()

    if key not in db:
        return jsonify({"status":"invalid"})

    now = time.time()

    if db[key]["device"] is None:

        db[key]["device"] = request.remote_addr
        db[key]["device_time"] = now
        save(db)

    remain = int(db[key]["expire"]-now)

    days = remain//86400
    hours = (remain%86400)//3600

    folder = f"{FILES}/{key}"

    files = os.listdir(folder) if os.path.exists(folder) else []

    return jsonify({
        "status":"ok",
        "days":days,
        "hours":hours,
        "files":files,
        "download":"/download/"+key
    })

# ---------------------
# DOWNLOAD
# ---------------------

@app.route("/download/<key>/<file>")
def download(key,file):

    return send_from_directory(f"{FILES}/{key}",file)

# ---------------------
# TRANSFER DEVICE
# ---------------------

@app.route("/api/transfer",methods=["POST"])
def transfer():

    key = request.json["key"]

    db = load()

    if key in db:
        db[key]["device"] = None
        db[key]["device_time"] = 0
        save(db)

    return jsonify({"status":"ok"})

# ---------------------

app.run(host="0.0.0.0",port=10000)
