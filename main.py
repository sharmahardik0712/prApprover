from flask import Flask, request, jsonify
import requests
import os
import json
from datetime import datetime
import secrets

app = Flask(__name__)

# Your GitHub token (used internally)
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
HEADERS = {
    "Authorization": f"token {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# File to store weekly secret
SECRET_FILE = "weekly_secret.json"

def generate_weekly_secret():
    """Generate a random 16-character secret for the current week and save it"""
    secret = secrets.token_urlsafe(16)
    current_week = datetime.utcnow().strftime("%Y-W%U")  # Year-WeekNumber
    data = {"week": current_week, "secret": secret}
    with open(SECRET_FILE, "w") as f:
        json.dump(data, f)
    return secret

def get_weekly_secret():
    """Return the current week's secret, generate new if missing or outdated"""
    current_week = datetime.utcnow().strftime("%Y-W%U")
    try:
        with open(SECRET_FILE, "r") as f:
            data = json.load(f)
            if data.get("week") == current_week:
                return data["secret"]
    except:
        pass
    return generate_weekly_secret()

@app.route('/')
def home():
    """Home page showing running status"""
    current_week = datetime.utcnow().strftime("%Y-W%U")
    return f"""
    <h1>PR Approver Service</h1>
    <p>Status: <strong>Running</strong></p>
    <p>Current Week: {current_week}</p>
    <p>Use the /approve endpoint to approve PRs with the weekly secret.</p>
    """

@app.route('/approve', methods=['POST'])
def approve_pr():
    data = request.json
    pr_url = data.get('pr_url')
    user_secret = data.get('secret')

    if not pr_url or not user_secret:
        return jsonify({"error": "PR URL and secret are required"}), 400

    # Check the secret
    if user_secret != get_weekly_secret():
        return jsonify({"error": "Invalid secret"}), 401

    try:
        # Extract owner, repo, and PR number from URL
        parts = pr_url.split('/')
        owner = parts[3]
        repo = parts[4]
        pr_number = parts[-1]

        api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pr_number}/reviews"
        payload = {"event": "APPROVE"}

        response = requests.post(api_url, headers=HEADERS, json=payload)

        if response.status_code == 200:
            return jsonify({"status": "approved"}), 200
        else:
            return jsonify({"error": response.json()}), response.status_code

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Print current week's secret for sharing (local use only)
    print("This week's secret:", get_weekly_secret())
    app.run(host='0.0.0.0', port=os.environ.get("PORT", 8080))


