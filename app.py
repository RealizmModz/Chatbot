# app.py
from dotenv import load_dotenv
load_dotenv()  # Load environment variables from .env

import os
import uuid
import time
from flask import Flask, render_template, session
from flask_socketio import SocketIO, emit
import openai
from pymongo import MongoClient

# Initialize Flask app and SocketIO
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")
socketio = SocketIO(app)

# Configure OpenAI API key
openai.api_key = os.environ.get("OPENAI_API_KEY")
if not openai.api_key:
    raise Exception("OPENAI_API_KEY not set")

# Connect to MongoDB with TLS settings (development only)
mongo_uri = os.environ.get("MONGO_URI")
if not mongo_uri:
    raise Exception("MONGO_URI not set")
client = MongoClient(mongo_uri, tls=True, tlsAllowInvalidCertificates=True)
db = client.get_database("chatbot_db")
conversations_collection = db.conversations

# Set threshold to summarize conversation history (adjust as needed)
SUMMARIZATION_THRESHOLD = 10  # Summarize when there are more than 10 messages

def summarize_conversation(context):
    """
    Summarize the provided conversation context into a concise summary.
    """
    try:
        prompt = "Summarize the following conversation in a few sentences:\n\n"
        for msg in context:
            prompt += f"{msg['role']}: {msg['message']}\n"
        
        messages_for_summary = [
            {"role": "system", "content": "You are a summarization assistant."},
            {"role": "user", "content": prompt}
        ]
        
        print("Sending summarization prompt:", prompt)
        summary_response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=messages_for_summary,
            max_tokens=150,
            temperature=0.5,
        )
        summary = summary_response.choices[0].message['content'].strip()
        print("Received summary:", summary)
        return summary
    except Exception as e:
        print("Error summarizing conversation:", e)
        return None

@app.route('/')
def index():
    # Assign a unique session ID if it doesn't exist
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    return render_template('index.html')

@socketio.on('send_message')
def handle_send_message(data):
    user_message = data.get("message")
    session_id = session.get("session_id")
    if not user_message or not session_id:
        emit("error", {"error": "Invalid message or session."})
        return

    current_time = time.time()
    
    print(f"Received user message: {user_message}")

    # Log the user's message with timestamp in MongoDB
    conversations_collection.insert_one({
        "session_id": session_id,
        "role": "user",
        "message": user_message,
        "timestamp": current_time
    })

    # Retrieve full conversation history sorted by time
    conversation_cursor = conversations_collection.find({"session_id": session_id}).sort("timestamp", 1)
    conversation_history = [{"role": "assistant" if msg["role"]=="bot" else "user", "content": msg["message"]} for msg in conversation_cursor]
    print("Current conversation history:", conversation_history)

    # If the conversation is too long, summarize older messages (keep last 5 intact)
    if len(conversation_history) > SUMMARIZATION_THRESHOLD:
        total_msgs = list(conversations_collection.find({"session_id": session_id}).sort("timestamp", 1))
        if len(total_msgs) > 5:
            older_context = []
            for msg in total_msgs[:-5]:
                older_context.append({"role": msg["role"], "message": msg["message"]})
            
            summary = summarize_conversation(older_context)
            if summary:
                # Delete older messages and insert summary message
                cutoff_time = total_msgs[-5]["timestamp"]
                conversations_collection.delete_many({
                    "session_id": session_id,
                    "timestamp": {"$lt": cutoff_time}
                })
                conversations_collection.insert_one({
                    "session_id": session_id,
                    "role": "bot",
                    "message": "Summary: " + summary,
                    "timestamp": time.time()
                })
                # Rebuild conversation history after summarization
                conversation_cursor = conversations_collection.find({"session_id": session_id}).sort("timestamp", 1)
                conversation_history = [{"role": "assistant" if msg["role"]=="bot" else "user", "content": msg["message"]} for msg in conversation_cursor]
                print("Conversation history after summarization:", conversation_history)

    # Append the latest user message for the API call
    conversation_history.append({"role": "user", "content": user_message})
    print("Final conversation history for API call:", conversation_history)

    # Call OpenAI API to generate a response
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=conversation_history,
            temperature=0.7,
        )
    except Exception as e:
        print("OpenAI API error:", e)
        emit("error", {"error": str(e)})
        return

    bot_message = response.choices[0].message['content']
    print("Bot response:", bot_message)

    # Log the bot's response with timestamp in MongoDB
    conversations_collection.insert_one({
        "session_id": session_id,
        "role": "bot",
        "message": bot_message,
        "timestamp": time.time()
    })

    # Emit the response back to the client
    emit("receive_message", {"message": bot_message})

if __name__ == '__main__':
    print("Starting Flask-SocketIO server...")
    # Run on 0.0.0.0 for Codespaces compatibility
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
