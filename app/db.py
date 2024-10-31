from pymongo import MongoClient
from config.config import Config

client = MongoClient(Config.MONGO_URI)
db = client["klimmzug_timer"]
participants = db["participants"]

def add_participant(data):
    return participants.insert_one(data).inserted_id

def get_participants(page, per_page, search=""):
    query = {"$or": [{"first_name": {"$regex": search, "$options": "i"}},
                     {"last_name": {"$regex": search, "$options": "i"}}]}
    return list(participants.find(query).skip(page * per_page).limit(per_page))

def update_time(participant_id, time):
    return participants.update_one({"_id": participant_id}, {"$set": {"time": time}})
