from flask import Flask, request
import requests
import os
import json

app = Flask(__name__)

# Load from environment or set manually
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN") or "YOUR_PAGE_ACCESS_TOKEN"
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN") or "your_custom_verify_token"
ROBLO_SECURITY_COOKIE = os.environ.get("ROBLO_SECURITY_COOKIE") or "YOUR_ROBLO_COOKIE"

# Config.json logic (hardcoded here for now)
GROUPS = [
    {
        "ID": 14086245,
        "NAME": "Digital Piano Org",
        "URL": "https://www.roblox.com/communities/14086245/Digital-Piano-Org#!/about"
    },
    {
        "ID": 5760800,
        "NAME": "Piano Simulator Community",
        "URL": "https://www.roblox.com/communities/5760800/Piano-Simulator-Community#!/about"
    },
    {
        "ID": 3793995,
        "NAME": "Funk Group",
        "URL": "https://www.roblox.com/communities/3793995/Funk-Group#!/about"
    }
]

# Endpoint for Facebook webhook verification
@app.route('/webhook', methods=['GET'])
def verify():
    if request.args.get("hub.mode") == "subscribe" and request.args.get("hub.verify_token") == VERIFY_TOKEN:
        return request.args.get("hub.challenge"), 200
    return "Verification failed", 403

# Handle incoming messages
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    for entry in data.get('entry', []):
        for messaging in entry.get('messaging', []):
            sender_id = messaging['sender']['id']
            message = messaging.get('message', {}).get('text', '').strip()

            if message.lower().startswith("check "):
                username = message[6:].strip()
                user_id = get_user_id(username)
                if not user_id:
                    send_message(sender_id, f"❌ Could not find a Roblox user named `{username}`.")
                else:
                    responses = []
                    for group in GROUPS:
                        status = is_user_eligible(user_id, group["ID"])
                        if status == "Eligible":
                            responses.append(f"✅ `{username}` is eligible for payouts on [{group['NAME']}]({group['URL']})")
                        elif status == "PayoutRestricted":
                            responses.append(f"❌ `{username}` is not yet eligible for payouts on [{group['NAME']}]({group['URL']})")
                        elif status == "NotInGroup":
                            responses.append(f"❌ `{username}` is not a member of [{group['NAME']}]({group['URL']})")
                        else:
                            responses.append(f"⚠ API error while checking [{group['NAME']}]")
                    send_message(sender_id, "\n".join(responses))
            else:
                send_message(sender_id, "📝 To check Roblox payout eligibility, type:\n`check <username>`")

    return "ok", 200

# Helper to get user ID from username
def get_user_id(username):
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [username], "excludeBannedUsers": True}
    headers = {"Content-Type": "application/json"}

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=10)
        data = res.json()
        if data["data"]:
            return data["data"][0]["id"]
    except:
        return None

# Helper to check payout eligibility
def is_user_eligible(user_id, group_id):
    url = f"https://economy.roblox.com/v1/groups/{group_id}/users-payout-eligibility?userIds={user_id}"
    headers = {
        "Cookie": f".ROBLOSECURITY={ROBLO_SECURITY_COOKIE}",
        "Accept": "application/json"
    }
    try:
        res = requests.get(url, headers=headers, timeout=10)
        data = res.json()
        return data.get("usersGroupPayoutEligibility", {}).get(str(user_id), "Unknown")
    except:
        return "APIError"

# Helper to send message
def send_message(recipient_id, text):
    url = "https://graph.facebook.com/v17.0/me/messages"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    headers = {"Content-Type": "application/json"}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text}
    }
    requests.post(url, params=params, headers=headers, json=payload)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
