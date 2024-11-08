from flask import Flask, jsonify, request
from pymongo import MongoClient
from bson import ObjectId
from datetime import datetime
import os

# Flask app setup
app = Flask(__name__)

# MongoDB client setup
mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017/klimmzug_timer")
client = MongoClient(mongo_uri)
db = client["klimmzug_timer"]
participants = db["participants"]

# Helper function to format ObjectId for JSON responses
def serialize_participant(participant):
    participant["_id"] = str(participant["_id"])
    return participant

# Routes
@app.route('/api/participant', methods=['POST'])
def create_participant():
    """Create a new participant."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    # Add timestamp of accepting the Datenschutzrichtlinie
    data['timestamp'] = datetime.now().isoformat()
    
    # Check for the signature in the data
    signature = data.get('signature')
    if not signature:
        return jsonify({"error": "No signature provided"}), 400
    
    participant_id = participants.insert_one(data).inserted_id
    return jsonify({"id": str(participant_id)}), 201

@app.route('/api/participant/<participant_id>', methods=['DELETE'])
def delete_participant(participant_id):
    """Delete a participant by ID."""
    result = participants.delete_one({"_id": ObjectId(participant_id)})
    if result.deleted_count == 0:
        return jsonify({"error": "Participant not found"}), 404
    return jsonify({"message": "Participant deleted"}), 200

@app.route('/api/participant/<participant_id>', methods=['PUT'])
def update_participant(participant_id):
    """Update a participant by ID."""
    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400
    
    result = participants.update_one({"_id": ObjectId(participant_id)}, {"$set": data})
    if result.matched_count == 0:
        return jsonify({"error": "Participant not found"}), 404
    return jsonify({"message": "Participant updated"}), 200

@app.route('/api/participants', methods=['GET'])
def list_participants():
    """List participants with pagination, search, and optional gender filter."""
    page = request.args.get("page")
    per_page = request.args.get("per_page")
    search = request.args.get("search", "")
    gender = request.args.get("gender", None)
    
    query = {"$or": [
        {"first_name": {"$regex": search, "$options": "i"}},
        {"last_name": {"$regex": search, "$options": "i"}}
    ]}
    
    if gender:
        query["gender"] = gender
    
    if page is None and per_page is None:
        # Return all participants if no pagination parameters are provided
        participants_list = list(participants.find(query))
    else:
        # Apply pagination
        page = int(page) if page is not None else 0
        per_page = int(per_page) if per_page is not None else 20
        participants_list = list(participants.find(query).skip(page * per_page).limit(per_page))
    
    participants_list = [serialize_participant(p) for p in participants_list]
    
    return jsonify(participants_list), 200

@app.route('/api/participant/<participant_id>/time', methods=['POST'])
def record_time(participant_id):
    """Record time for a participant."""
    time = request.json.get("time")
    if time is None:
        return jsonify({"error": "No time provided"}), 400
    
    result = participants.update_one({"_id": ObjectId(participant_id)}, {"$set": {"time": time}})
    if result.matched_count == 0:
        return jsonify({"error": "Participant not found"}), 404
    
    return jsonify({"status": "success"}), 200

# Ensure app runs if file is executed directly
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
