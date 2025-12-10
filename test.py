import os
import json
import yaml
import unittest
from unittest.mock import patch, MagicMock
import entrypoint

def createGitHubEvent(user, command):
    event = {
        "comment": {
                "body": command,
                "user": {"login": user}
            },
        "issue": {"number": 42},
        "repository": {"full_name": "test/repo"}
    }
    with open("event.json", "w") as f:
        json.dump(event, f)

class TestOwnersBot(unittest.TestCase):
    def setUp(self):
        # 1. Create a dummy OWNERS file
        self.owners_data = {
            "approvers": ["approver"],
            "reviewers": ["approver", "reviewer"]
        }
        with open("OWNERS", "w") as f:
            yaml.dump(self.owners_data, f)

        os.environ["GITHUB_TOKEN"] = "dummy-token"
        os.environ["OWNERS_FILE"] = "OWNERS"
        os.environ["GITHUB_EVENT_PATH"] = "event.json"
        os.environ["GITHUB_WORKSPACE"] = os.getcwd()

    def tearDown(self):
        if os.path.exists("OWNERS"): os.remove("OWNERS")
        if os.path.exists("event.json"): os.remove("event.json")

    @patch('requests.post')
    @patch('requests.delete')
    def test_lgtm_success(self, mock_delete, mock_post):
        print("\n--- Testing Valid /lgtm ---")

        createGitHubEvent("reviewer", "/lgtm")
        entrypoint.main()

        mock_post.assert_called_with(
            "https://api.github.com/repos/test/repo/issues/42/labels",
            json={"labels": ["lgtm"]},
            headers={'Authorization': 'Bearer dummy-token', 'Accept': 'application/vnd.github.v3+json'}
        )
        print("✅ Success: /lgtm added label.")

    @patch('requests.post')
    def test_unauthorized_lgtm(self, mock_post):
        print("\n--- Testing Unauthorized User ---")

        createGitHubEvent("unathorized", "/lgtm")
        entrypoint.main()

        mock_post.assert_not_called()
        print("✅ Success: Random user was ignored.")

    @patch('requests.post')
    def test_unauthorized_approve(self, mock_post):
        print("\n--- Testing Unauthorized User ---")

        createGitHubEvent("unathorized", "/approve")
        entrypoint.main()

        mock_post.assert_not_called()
        print("✅ Success: Random user was ignored.")

    @patch('requests.delete')
    def test_lgtm_cancel(self, mock_delete):
        print("\n--- Testing /lgtm cancel ---")

        createGitHubEvent("reviewer", "/lgtm cancel")
        entrypoint.main()

        mock_delete.assert_called_with(
            "https://api.github.com/repos/test/repo/issues/42/labels/lgtm",
            headers={'Authorization': 'Bearer dummy-token', 'Accept': 'application/vnd.github.v3+json'}
        )
        print("✅ Success: Label removed.")

    @patch('requests.delete')
    def test_unauthorized_lgtm_cancel(self, mock_delete):
        print("\n--- Testing unathorized /lgtm cancel ---")

        createGitHubEvent("unathorized", "/lgtm cancel")
        entrypoint.main()

        mock_delete.assert_not_called()
        print("✅ Success: Label was not removed.")

    @patch('requests.delete')
    def test_unauthorized_approve_cancel(self, mock_delete):
        print("\n--- Testing unathorized /approve cancel ---")

        createGitHubEvent("reviewer", "/approve cancel")
        entrypoint.main()

        mock_delete.assert_not_called()
        print("✅ Success: Label was not removed.")

    @patch('requests.delete')
    def test_approve_cancel(self, mock_delete):
        print("\n--- Testing /approve cancel ---")

        createGitHubEvent("approve", "/approve cancel")
        entrypoint.main()

        mock_delete.assert_not_called()
        print("✅ Success: Label was not removed.")

if __name__ == '__main__':
    unittest.main()
