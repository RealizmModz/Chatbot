import os
from flask import Flask, render_template, request, jsonify
import openai
from pymongo import MongoClient

# Initialize Flask app
app = Flask(__name__)

# Configure OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")
if not openai.api_key:
    raise Exception("OPENAI_API_KEY not set")

# Connect to MongoDB
mongo_uri = os.environ.get("MONGO_URI")
if not mongo_uri:
    raise Exception("MONGO_URI not set")
client = MongoClient(mongo_uri)
db = client.get_database("chatbot_db")
conversations_collection = db.conversations

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    user_message = request.json.get("message")
    if not user_message:
        return jsonify({"error": "No message provided"}), 400

    # Log user's message to MongoDB
    conversations_collection.insert_one({"message": user_message, "role": "user"})

    # Call the OpenAI API (using GPT-3.5 Turbo for this example)
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": user_message}],
            temperature=0.7,
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    bot_message = response.choices[0].message['content']

    # Log bot's response to MongoDB
    conversations_collection.insert_one({"message": bot_message, "role": "bot"})

    return jsonify({"message": bot_message})

if __name__ == '__main__':
    app.run(debug=True)
