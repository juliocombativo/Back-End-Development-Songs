from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################

@app.route("/health")
def health():
    return jsonify(dict(status="OK")), 200

@app.route("/count")
def count():
    """return the number of songs on the db"""
    count = db.songs.count_documents({})
    return jsonify(dict(count=count)), 200

@app.route("/song", methods=["GET"])
def songs():
    """Query all the songs on the db"""
    all_songs = db.songs.find({})
    return {songs:parse_json(all_songs)}, 200

@app.route("/song/<int:id>", methods=["GET"])
def get_song_by_id(id):
    """Query for the song with the given ID from the db"""
    song = db.songs.find_one({"id":id})
    if song:
        return parse_json(song), 200
    return {"message": "song with id not found"}, 404

@app.route("/song", methods=["POST"])
def create_song():
    """Add the given song to the db"""
    song = request.json
    found_song = db.songs.find_one({"id":song['id']})
    if found_song:
        return {"Message": f"song with id {song['id']} already present"}, 302
    inserted = db.songs.insert_one(song)
    return {"inserted id": {"$oid": str(inserted.inserted_id)}}, 201

@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    """Update the information relevant to the the song with the given ID"""
    song = request.json
    find_filter = {"id":id}
    found_song = db.songs.find_one(find_filter)
    if found_song:
        updated = db.songs.update_one(find_filter, {"$set":song}, False)
        song['_id'] = {"$oid":str(found_song["_id"])}
        return jsonify(song), 201
    return {"message": "song not found"}, 404

@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    """Delete the song with the given id from the DB"""
    result = db.songs.delete_one({"id":id})
    if result.deleted_count == 1:
        return "", 204
    return {"message": "song not found"}, 404
