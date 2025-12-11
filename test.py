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
    def test_unprotected_label_ignored(self, mock_post, mock_delete):
        print("\n--- Testing Unprotected Label Ignored ---")

        createLabelEvent("random-user", "labeled", "bug")
        entrypoint.main()

        mock_delete.assert_not_called()
        mock_post.assert_not_called()
        print("✅ Success: Unprotected label was ignored.")

    @patch('requests.post')
    def test_hold_success(self, mock_post):
        print("\n--- Testing Valid /hold ---")

        createGitHubEvent("approver", "/hold")
        entrypoint.main()

        mock_post.assert_called_with(
            "https://api.github.com/repos/test/repo/issues/42/labels",
            json={"labels": ["hold"]},
            headers={'Authorization': 'Bearer dummy-token', 'Accept': 'application/vnd.github.v3+json'}
        )
        print("✅ Success: /hold added label.")

    @patch('requests.post')
    def test_unauthorized_hold(self, mock_post):
        print("\n--- Testing Unauthorized /hold ---")

        createGitHubEvent("reviewer", "/hold")
        entrypoint.main()

        mock_post.assert_not_called()
        print("✅ Success: Reviewer cannot add hold label.")

    @patch('requests.delete')
    def test_hold_cancel(self, mock_delete):
        print("\n--- Testing /hold cancel ---")

        createGitHubEvent("approver", "/hold cancel")
        entrypoint.main()

        mock_delete.assert_called_with(
            "https://api.github.com/repos/test/repo/issues/42/labels/hold",
            headers={'Authorization': 'Bearer dummy-token', 'Accept': 'application/vnd.github.v3+json'}
        )
        print("✅ Success: Hold label removed.")

    @patch('requests.delete')
    def test_unauthorized_hold_cancel(self, mock_delete):
        print("\n--- Testing unauthorized /hold cancel ---")

        createGitHubEvent("reviewer", "/hold cancel")
        entrypoint.main()

        mock_delete.assert_not_called()
        print("✅ Success: Reviewer cannot remove hold label.")

    @patch('requests.post')
    def test_exactly_hold(self, mock_post):
        print("\n--- Testing random/hold doesn't get treated as /hold ---")

        createGitHubEvent("approver", "random/hold")
        entrypoint.main()

        mock_post.assert_not_called()
        print("✅ Success: command ignored.")

    @patch('requests.put')
    @patch('requests.get')
    def test_merge_when_ready(self, mock_get, mock_put):
        print("\n--- Testing PR merges when lgtm and approved labels present ---")

        createGitHubEvent("approver", "/approve")

        # Mock the GET request to return PR with both labels
        mock_pr_response = MagicMock()
        mock_pr_response.status_code = 200
        mock_pr_response.json.return_value = {
            "labels": [
                {"name": "lgtm"},
                {"name": "approved"}
            ]
        }
        mock_get.return_value = mock_pr_response

        # Mock successful merge
        mock_merge_response = MagicMock()
        mock_merge_response.status_code = 200
        mock_put.return_value = mock_merge_response

        entrypoint.main()

        mock_put.assert_called_with(
            "https://api.github.com/repos/test/repo/pulls/42/merge",
            json={"merge_strategy": "merge"},
            headers={'Authorization': 'Bearer dummy-token', 'Accept': 'application/vnd.github.v3+json'}
        )
        print("✅ Success: PR merged when ready.")

    @patch('requests.put')
    @patch('requests.get')
    def test_no_merge_when_only_lgtm(self, mock_get, mock_put):
        print("\n--- Testing PR doesn't merge with only lgtm label ---")

        createGitHubEvent("reviewer", "/lgtm")

        # Mock the GET request to return PR with only lgtm
        mock_pr_response = MagicMock()
        mock_pr_response.status_code = 200
        mock_pr_response.json.return_value = {
            "labels": [
                {"name": "lgtm"}
            ]
        }
        mock_get.return_value = mock_pr_response

        entrypoint.main()

        mock_put.assert_not_called()
        print("✅ Success: PR not merged with only lgtm.")

    @patch('requests.put')
    @patch('requests.get')
    def test_no_merge_when_only_approved(self, mock_get, mock_put):
        print("\n--- Testing PR doesn't merge with only approved label ---")

        createGitHubEvent("approver", "/approve")

        # Mock the GET request to return PR with only approved
        mock_pr_response = MagicMock()
        mock_pr_response.status_code = 200
        mock_pr_response.json.return_value = {
            "labels": [
                {"name": "approved"}
            ]
        }
        mock_get.return_value = mock_pr_response

        entrypoint.main()

        mock_put.assert_not_called()
        print("✅ Success: PR not merged with only approved.")

    @patch('requests.put')
    @patch('requests.get')
    def test_no_merge_when_hold_present(self, mock_get, mock_put):
        print("\n--- Testing PR doesn't merge when hold label present ---")

        createGitHubEvent("approver", "/approve")

        # Mock the GET request to return PR with all labels including hold
        mock_pr_response = MagicMock()
        mock_pr_response.status_code = 200
        mock_pr_response.json.return_value = {
            "labels": [
                {"name": "lgtm"},
                {"name": "approved"},
                {"name": "hold"}
            ]
        }
        mock_get.return_value = mock_pr_response

        entrypoint.main()

        mock_put.assert_not_called()
        print("✅ Success: PR not merged when hold is present.")

    @patch('requests.put')
    @patch('requests.get')
    def test_merge_with_squash_strategy(self, mock_get, mock_put):
        print("\n--- Testing PR merges with squash strategy ---")

        os.environ["MERGE_STRATEGY"] = "squash"
        createGitHubEvent("approver", "/approve")

        # Mock the GET request to return PR with both labels
        mock_pr_response = MagicMock()
        mock_pr_response.status_code = 200
        mock_pr_response.json.return_value = {
            "labels": [
                {"name": "lgtm"},
                {"name": "approved"}
            ]
        }
        mock_get.return_value = mock_pr_response

        # Mock successful merge
        mock_merge_response = MagicMock()
        mock_merge_response.status_code = 200
        mock_put.return_value = mock_merge_response

        entrypoint.main()

        mock_put.assert_called_with(
            "https://api.github.com/repos/test/repo/pulls/42/merge",
            json={"merge_strategy": "squash"},
            headers={'Authorization': 'Bearer dummy-token', 'Accept': 'application/vnd.github.v3+json'}
        )

        # Clean up
        if "MERGE_STRATEGY" in os.environ:
            del os.environ["MERGE_STRATEGY"]

        print("✅ Success: PR merged with squash strategy.")

    @patch('requests.put')
    @patch('requests.get')
    def test_merge_with_rebase_strategy(self, mock_get, mock_put):
        print("\n--- Testing PR merges with rebase strategy ---")

        os.environ["MERGE_STRATEGY"] = "rebase"
        createGitHubEvent("approver", "/approve")

        # Mock the GET request to return PR with both labels
        mock_pr_response = MagicMock()
        mock_pr_response.status_code = 200
        mock_pr_response.json.return_value = {
            "labels": [
                {"name": "lgtm"},
                {"name": "approved"}
            ]
        }
        mock_get.return_value = mock_pr_response

        # Mock successful merge
        mock_merge_response = MagicMock()
        mock_merge_response.status_code = 200
        mock_put.return_value = mock_merge_response

        entrypoint.main()

        mock_put.assert_called_with(
            "https://api.github.com/repos/test/repo/pulls/42/merge",
            json={"merge_strategy": "rebase"},
            headers={'Authorization': 'Bearer dummy-token', 'Accept': 'application/vnd.github.v3+json'}
        )

        # Clean up
        if "MERGE_STRATEGY" in os.environ:
            del os.environ["MERGE_STRATEGY"]

        print("✅ Success: PR merged with rebase strategy.")

    @patch('requests.put')
    @patch('requests.get')
    @patch('requests.post')
    def test_auto_merge_disabled(self, mock_post, mock_get, mock_put):
        print("\n--- Testing auto-merge disabled ---")

        os.environ["AUTO_MERGE"] = "false"
        createGitHubEvent("approver", "/approve")

        # Mock the GET request to return PR with both labels
        mock_pr_response = MagicMock()
        mock_pr_response.status_code = 200
        mock_pr_response.json.return_value = {
            "labels": [
                {"name": "lgtm"},
                {"name": "approved"}
            ]
        }
        mock_get.return_value = mock_pr_response

        entrypoint.main()

        # Label should still be added
        mock_post.assert_called()
        # But merge should not happen
        mock_put.assert_not_called()

        # Clean up
        if "AUTO_MERGE" in os.environ:
            del os.environ["AUTO_MERGE"]

        print("✅ Success: Auto-merge was disabled.")

if __name__ == '__main__':
    unittest.main()
