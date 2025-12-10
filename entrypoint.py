import os
import yaml
import requests
import json
import sys

def main():
    token = os.environ.get("GITHUB_TOKEN")
    owners_path = os.environ.get("OWNERS_FILE")

    event_path = os.environ.get("GITHUB_EVENT_PATH")
    if not event_path:
        print("No event path found. Is this running in GitHub Actions?")
        sys.exit(1)

    with open(event_path, 'r') as f:
        event = json.load(f)
    try:
        comment_body = event['comment']['body'].lower().strip()
        comment_author = event['comment']['user']['login']
        pr_number = event['issue']['number']
        repo_full_name = event['repository']['full_name']
    except KeyError:
        print("Event does not appear to be a comment on an issue/PR.")
        sys.exit(0)

    workspace = os.environ.get("GITHUB_WORKSPACE", ".")
    full_owners_path = os.path.join(workspace, owners_path)

    print(f"Reading OWNERS from: {full_owners_path}")

    try:
        with open(full_owners_path, "r") as f:
            owners_data = yaml.safe_load(f)
    except FileNotFoundError:
        print(f"ERROR: Could not find {owners_path} in the repository root.")
        sys.exit(1)

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

    # Add labels here
    if comment_body.startswith("/lgtm"):
        if comment_author in reviewers:
            if "cancel" in comment_body:
                remove_label("lgtm")
            else:
                add_label("lgtm")
        else:
            print(f"User {comment_author} is not in 'reviewers' list.")

    elif comment_body.startswith("/approve"):
        if comment_author in approvers:
            if "cancel" in comment_body:
                remove_label("approved")
            else:
                add_label("approved")
        else:
            print(f"User {comment_author} is not in 'approvers' list.")

if __name__ == "__main__":
    main()
