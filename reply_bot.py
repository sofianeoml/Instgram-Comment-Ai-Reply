from instagrapi import Client
import json
import time
from pymongo import MongoClient
from datetime import datetime
import google.generativeai as genai


genai.configure(api_key="api_key")
model = genai.GenerativeModel("gemini-1.5-flash")
    
    
# MongoDB setup for tracking replied comments
mongo_client = MongoClient("mongodb://localhost:27017/")
db = mongo_client["instagram_bot"]
collection = db["replied_comments"]

# Load and save cookies for login persistence
def load_cookies():
    try:
        with open('cookies.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def save_cookies(client):
    with open('cookies.json', 'w') as f:
        json.dump(client.get_settings(), f)

# Initialize the Instagram client
client = Client()

# Load cookies and attempt to log in
cookies = load_cookies()
if cookies:
    client.set_settings(cookies)
else:
    # Perform login and save cookies if not found
    username = 'username'
    password = 'password'
    client.login(username, password)
    save_cookies(client)

# Verify that the user ID was obtained
user_id = client.user_id
print(f"Logged in as user ID: {user_id}")

# Function to check if a comment has been replied to
def has_replied(comment_id):
    return collection.find_one({"comment_id": comment_id}) is not None

# Function to log a reply in the database
def log_reply(comment_id, reply_text, comment_text):
    collection.insert_one({
        "comment_id": comment_id,
        "reply_text": reply_text,
        "comment_text": comment_text,
        "replied_at": datetime.now()
    })

# Generate reply content (replace with GPT integration if needed)
def generate_reply(comment_text):
    response = model.generate_content(f"Analyze the Instagram comment provided below and create a friendly, helpful response that matches the tone and context of the user's question or statement. The response should aim to provide value, express gratitude, or answer the user’s query in an engaging and approachable way. If the comment includes a question, provide an informative answer with a call to action, if relevant. and reply most be start with [REPLY-AI]. Comment: {comment_text}")
    return(response.text)

# Reply to latest post comments
def reply_to_latest_post_comments():
    recent_media = client.user_medias(user_id, 1)
    if not recent_media:
        print("No posts found on this account.")
        return

    latest_media_id = recent_media[0].id
    print(f"Found latest post with ID: {latest_media_id}")

    comments = client.media_comments(latest_media_id)
    for comment in comments:
        comment_id = comment.pk
        comment_text = comment.text
        comment_user = comment.user.username
        comment_user_id = comment.user.pk  # User ID of the comment author
        
        # Check if the comment has already been replied to and if it’s not from the bot’s own user ID
        if has_replied(comment_id):
            print(f"Already replied to comment ID: {comment_id}")
        elif int(comment_user_id) == int(user_id):
            print(f"Skipping comment from the bot's own account (ID: {comment_id})")
        else:
            # Generate reply and post it
            reply_text = generate_reply(comment_text)
            try:
                client.media_comment(media_id=latest_media_id, text=reply_text, replied_to_comment_id=comment_id)
                print(f"Replied to comment ID {comment_id}: {reply_text}")
                log_reply(comment_id, reply_text, comment_text)  # Log reply
                time.sleep(2)  # Avoid rate limits
            except Exception as e:
                print(f"Failed to post reply to comment ID {comment_id}: {e}")


# Run the function on a schedule
while True:
    reply_to_latest_post_comments()
    time.sleep(300)  # Run every 5 minutes
