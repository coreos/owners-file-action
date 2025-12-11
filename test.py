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

def createLabelEvent(user, action, label):
    """Create a label event (labeled or unlabeled)."""
    event = {
        "action": action,
        "pull_request": {"number": 42},
        "label": {"name": label},
        "sender": {"login": user},
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
    def test_lgtm_success(self, mock_post):
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

        createGitHubEvent("approver", "/approve cancel")
        entrypoint.main()

        mock_delete.assert_called_with(
            "https://api.github.com/repos/test/repo/issues/42/labels/approved",
            headers={'Authorization': 'Bearer dummy-token', 'Accept': 'application/vnd.github.v3+json'}
        )
        print("✅ Success: Label removed.")

    @patch('requests.post')
    def test_exactly_approve(self, mock_post):
        print("\n--- Testing random/approve doesn't get treated as /approve ---")

        createGitHubEvent("approver", "random/approve")
        entrypoint.main()

        mock_post.assert_not_called()
        print("✅ Success: command ignored.")

    @patch('requests.post')
    def test_exactly_lgtm(self, mock_post):
        print("\n--- Testing random/lgtm doesn't get treated as /lgtm ---")

        createGitHubEvent("reviewer", "random/lgtm")
        entrypoint.main()

        mock_post.assert_not_called()
        print("✅ Success: command ignored.")

    @patch('requests.delete')
    def test_unauthorized_label_addition(self, mock_delete):
        print("\n--- Testing Unauthorized Label Addition ---")

        createLabelEvent("random-user", "labeled", "lgtm")
        entrypoint.main()

        mock_delete.assert_called_with(
            "https://api.github.com/repos/test/repo/issues/42/labels/lgtm",
            headers={'Authorization': 'Bearer dummy-token', 'Accept': 'application/vnd.github.v3+json'}
        )
        print("✅ Success: Unauthorized label addition was reverted.")

    @patch('requests.post')
    def test_unauthorized_label_removal(self, mock_post):
        print("\n--- Testing Unauthorized Label Removal ---")

        createLabelEvent("random-user", "unlabeled", "approved")
        entrypoint.main()

        mock_post.assert_called_with(
            "https://api.github.com/repos/test/repo/issues/42/labels",
            json={"labels": ["approved"]},
            headers={'Authorization': 'Bearer dummy-token', 'Accept': 'application/vnd.github.v3+json'}
        )
        print("✅ Success: Unauthorized label removal was reverted.")

    @patch('requests.delete')
    @patch('requests.post')
    def test_bot_label_addition_allowed(self, mock_post, mock_delete):
        print("\n--- Testing Bot Label Addition Allowed ---")

        os.environ["GITHUB_ACTOR"] = "github-actions[bot]"
        createLabelEvent("github-actions[bot]", "labeled", "lgtm")
        entrypoint.main()

        mock_delete.assert_not_called()
        mock_post.assert_not_called()
        print("✅ Success: Bot's own label addition was not reverted.")
        del os.environ["GITHUB_ACTOR"]

    @patch('requests.delete')
    @patch('requests.post')
    def test_bot_label_removal_allowed(self, mock_post, mock_delete):
        print("\n--- Testing Bot Label Removal Allowed ---")

        os.environ["GITHUB_ACTOR"] = "github-actions[bot]"
        createLabelEvent("github-actions[bot]", "unlabeled", "approved")
        entrypoint.main()

        mock_delete.assert_not_called()
        mock_post.assert_not_called()
        print("✅ Success: Bot's own label removal was not reverted.")
        del os.environ["GITHUB_ACTOR"]

    @patch('requests.delete')
    @patch('requests.post')
    def test_unprotected_label_ignored(self, mock_post, mock_delete):
        print("\n--- Testing Unprotected Label Ignored ---")

        createLabelEvent("random-user", "labeled", "bug")
        entrypoint.main()

        mock_delete.assert_not_called()
        mock_post.assert_not_called()
        print("✅ Success: Unprotected label was ignored.")

if __name__ == '__main__':
    unittest.main()
