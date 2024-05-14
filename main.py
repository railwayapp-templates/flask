#!/usr/bin/env python3
from flask import Flask, request, jsonify
import time, requests, hashlib, os, sys, json, flask, redis
from farcaster import Warpcast
from dotenv import load_dotenv

def ts(string):
    # Function to format timestamp for logs
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {string}")

def witness(data):
    # Function to hash the data and submit to Witness.co API
    hash_object = hashlib.sha256(data.encode('utf-8'))
    hex_dig = hash_object.hexdigest()
    hash = "0x" + hex_dig
    # Submit hash
    json_data = {
        'leafHash': hash,
    }

    req = requests.post('https://api.witness.co/postLeafHash', json=json_data)
    if req.status_code == 200:
        # Get URL
        witness_url = "https://scan.witness.co/leaf/{}".format(hash)
        return hash, witness_url
    else:
        ts("Witness API Error  - {}".format(str(req.status_code)))
        ts(req.text)
        # TODO add error handling/retries
        return None, None

def read_db():
    # Function to read the database
    db_raw = r.get('db')
    if db_raw:
        db = json.loads(db_raw)
        return db
    else:
        return None

def write_db(db):
    # Function to write to the database
    r.set('db', json.dumps(db))

def check_for_db():
    # Function to check for the database
    db = read_db()
    if db is None:
        ts("Redis DB not found - Initializing")
        db = {'last_mention_id': 0, 'old_mentions': []}
        write_db(db)
    else:
        ts("Redis DB Loaded")
    return db

app = Flask(__name__)

@app.route('/hi', methods=['GET'])
def hello_world():
    print("Hello, World!")
    return jsonify({"Hello": "Hello World"})

@app.route('/api', methods=['POST'])
def webhook():
    print("Webhook Triggered: {}".format(request.json))
    n = request.json["data"]
    new_mention = {"id": n["hash"], "username":n["author"]["username"], "fid": str(n["author"]["fid"]), "text": n["text"]}
    global r
    r = redis.Redis(host=os.getenv('REDISHOST'), port=os.getenv('REDISPORT'), password=os.getenv('REDISPASSWORD'))
    db = check_for_db()
    seed_phrase = os.getenv('FARCASTER_PHRASE')
    neynar_api = os.getenv('NEYNAR_API')
    if not seed_phrase:
        ts("FARCASTER_PHRASE environment variable not found.")
        sys.exit(1)
    client = Warpcast(seed_phrase, rotation_duration=1)
    if client.get_healthcheck():
        old_mentions_set = set(o["id"] for o in db["old_mentions"])
        if n["hash"] in old_mentions_set:
            ts("Not a new mention")
        else:
            ts("New Mention: {} said {}".format(n["author"]["displayName"], n["text"]))
            warp_url = "https://warpcast.com/{}/{}".format(n["username"], n["id"])
            hash, witness_url = witness(warp_url)
            if hash and witness_url is not None:
                ts("Posting cast: {}".format(n["id"]))
                req = client.post_cast(witness_url, parent={'type': 'cast-mention', 'fid': n["fid"], 'hash': n["id"]})
                if req.cast.hash:
                    ts("New Cast: {}".format("https://warpcast.com/{}/{}".format(req.cast.author.username, req.cast.hash)))
                else:
                    ts("Failed to post cast")
                    ts(str(req)) # TODO add error handling
            else:
                ts("Witness API error handling failed") # TODO add db handling for new_mentions that don't get tweets produced during API downtime
            db = {'last_mention_id': n["hash"], 'old_mentions': [new_mention] + db["old_mentions"]}
            write_db(db)
    else:
        ts("Error - Client failed healthcheck")
    return '', 200

if __name__ == '__main__':
    app.run(debug=True, port=os.getenv("PORT", default=5000))
