import os
import yaml
import requests
import json
import sys

def is_bot_action(event):
    """Check if the current action is performed by the bot itself."""
    actor = event.get('sender', {}).get('login', '')
    github_actor = os.environ.get('GITHUB_ACTOR', '')
    return actor == github_actor or 'bot' in actor.lower()

def is_protected_label(label_name):
    return label_name in ['lgtm', 'approved']

def handle_label_event(event, token):
    """Handle label added/removed events to protect bot-managed labels."""
    action = event.get('action')
    if action not in ['labeled', 'unlabeled']:
        print(f"Not a label event (action: {action})")
        return

    if is_bot_action(event):
        print("Label change by bot itself, skipping protection check")
        return

    label_name = event.get('label', {}).get('name', '')
    if not is_protected_label(label_name):
        print(f"Label '{label_name}' is not protected, ignoring")
        return

    pr_number = event.get('pull_request', {}).get('number')
    repo_full_name = event.get('repository', {}).get('full_name', '')
    actor = event.get('sender', {}).get('login', 'unknown')

    api_url = f"https://api.github.com/repos/{repo_full_name}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    if action == 'labeled':
        # Unauthorized addition - remove the label
        print(f"Unauthorized addition of '{label_name}' label by {actor}, removing it")
        requests.delete(f"{api_url}/issues/{pr_number}/labels/{label_name}", headers=headers)
    elif action == 'unlabeled':
        # Unauthorized removal - add the label back
        print(f"Unauthorized removal of '{label_name}' label by {actor}, adding it back")
        requests.post(f"{api_url}/issues/{pr_number}/labels", json={"labels": [label_name]}, headers=headers)

def handle_comment_event(event, token, owners_path):
    """Handle comment events for /lgtm and /approve commands."""
    try:
        comment_body = event['comment']['body'].lower().strip()
        comment_author = event['comment']['user']['login']
        pr_number = event['issue']['number']
        repo_full_name = event['repository']['full_name']
    except KeyError:
        print("Event does not appear to be a comment on an issue/PR.")
        return

    workspace = os.environ.get("GITHUB_WORKSPACE", ".")
    full_owners_path = os.path.join(workspace, owners_path)

    print(f"Reading OWNERS from: {full_owners_path}")

    try:
        with open(full_owners_path, "r") as f:
            owners_data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"ERROR: Could not find {owners_path} in the repository root.")
        return

    approvers = owners_data.get("approvers", [])
    reviewers = owners_data.get("reviewers", [])

    api_url = f"https://api.github.com/repos/{repo_full_name}"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    def add_label(label):
        print(f"Adding label: {label}")
        requests.post(f"{api_url}/issues/{pr_number}/labels", json={"labels": [label]}, headers=headers)

    def remove_label(label):
        print(f"Removing label: {label}")
        requests.delete(f"{api_url}/issues/{pr_number}/labels/{label}", headers=headers)

    words = comment_body.split()

    if "/lgtm" in words:
        if comment_author in reviewers:
            if "/lgtm cancel" in comment_body:
                remove_label("lgtm")
            else:
                add_label("lgtm")
        else:
            print(f"User {comment_author} is not in 'reviewers' list.")

    if "/approve" in words:
        if comment_author in approvers:
            if "/approve cancel" in comment_body:
                remove_label("approved")
            else:
                add_label("approved")
        else:
            print(f"User {comment_author} is not in 'approvers' list.")

def main():
    token = os.environ.get("GITHUB_TOKEN")
    owners_path = os.environ.get("OWNERS_FILE")

    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("No event path found. Is this running in GitHub Actions?")
        sys.exit(1)

    with open(event_path, 'r') as f:
        event = json.load(f)

    if 'pull_request' in event and event.get('action') in ['labeled', 'unlabeled']:
        print(f"Detected label event: {event.get('action')}")
        handle_label_event(event, token)
    elif 'comment' in event:
        print("Detected comment event")
        handle_comment_event(event, token, owners_path)
    else:
        print("Event type not recognized or not supported")
        sys.exit(0)

if __name__ == "__main__":
    main()
