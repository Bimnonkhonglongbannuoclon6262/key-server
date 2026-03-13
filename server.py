from flask import Flask, request, jsonify, send_from_directory, render_template, redirect
import os
import json
import time
import uuid

app = Flask(__name__)

DB = "keys.json"
FILES = "keyfiles"

RESET_TIME = 7200  # 2h

os.makedirs(FILES, exist_ok=True)

# ---------------- DATABASE ----------------

def load():
    if not os.path.exists(DB):
        return {}
    with open(DB) as f:
        return json.load(f)

def save(data):
    with open(DB,"w") as f:
        json.dump(data,f,indent=4)

# ---------------- CLEAN ----------------

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

        # reset IP sau 2h
        if db[k]["device"]:

            if now - db[k]["device_time"] > RESET_TIME:

                db[k]["device"] = None
                db[k]["device_time"] = 0
                changed = True

    if changed:
        save(db)

# ---------------- PANEL ----------------

@app.route("/")
def panel():

    clean()

    db = load()

    keys = []

    for k,v in db.items():

        remain = int(v["expire"] - time.time())

        days = remain//86400
        hours = (remain%86400)//3600

        keys.append({
            "key":k,
            "days":days,
            "hours":hours,
            "device":v["device"]
        })

    return render_template("panel.html",keys=keys)

# ---------------- CREATE KEY ----------------

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

# ---------------- DELETE KEY ----------------

@app.route("/delete/<key>")
def delete(key):

    db = load()

    if key in db:
        del db[key]
        save(db)

    return redirect("/")

# ---------------- AUTHORIZE PANEL ----------------

@app.route("/authorize/<key>")
def authorize(key):

    db = load()

    if key in db:

        db[key]["device"] = None
        db[key]["device_time"] = 0

        save(db)

    return redirect("/")

# ---------------- UPLOAD FILE ----------------

@app.route("/upload/<key>",methods=["POST"])
def upload(key):

    file = request.files["file"]

    path = f"{FILES}/{key}"

    os.makedirs(path,exist_ok=True)

    file.save(os.path.join(path,file.filename))

    return redirect("/")

# ---------------- CLIENT CHECK ----------------

@app.route("/api/check",methods=["POST"])
def check():

    clean()

    key = request.json["key"]

    db = load()

    if key not in db:
        return jsonify({"status":"invalid"})

    ip = request.remote_addr
    now = time.time()

    # đăng nhập lần đầu
    if db[key]["device"] is None:

        db[key]["device"] = ip
        db[key]["device_time"] = now
        save(db)

    # thiết bị khác
    elif db[key]["device"] != ip:

        return jsonify({"status":"locked"})

    remain = int(db[key]["expire"] - now)

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

# ---------------- DOWNLOAD ----------------

@app.route("/download/<key>/<file>")
def download(key,file):

    return send_from_directory(f"{FILES}/{key}",file)

# ---------------- CLIENT AUTHORIZE ----------------

@app.route("/api/authorize",methods=["POST"])
def authorize_client():

    key = request.json["key"]

    db = load()

    if key in db:

        db[key]["device"] = None
        db[key]["device_time"] = 0

        save(db)

    return jsonify({
        "status":"ok",
        "delete_files":True
    })

# ---------------- RUN ----------------

import os

if __name__ == "__main__":

    port = int(os.environ.get("PORT",10000))

    app.run(host="0.0.0.0",port=port)
