# Owners Files Action

A GitHub Action that handles `/lgtm`, `/approve`, and `/hold` commands on pull requests based on an OWNERS file.

## Features

- Responds to `/lgtm`, `/approve`, and `/hold` comments on pull requests
- Validates commenters against an OWNERS file
- Automatically adds labels to PRs based on approvals
- Prevents unauthorized manual label changes (protects `lgtm` and `approved` labels)
- Auto-merges PRs when both `lgtm` and `approved` labels are present (and no `hold` label)
- Configurable merge strategy (merge, squash, or rebase)

## Usage

Create a workflow file (e.g., `.github/workflows/owners.yml`):

```yaml
name: Owners File Action

on:
  issue_comment:
    types: [created]
  pull_request:
    types: [labeled, unlabeled]

jobs:
  handle-events:
    if: >-
      github.event_name == 'pull_request' ||
      (github.event_name == 'issue_comment' && github.event.issue.pull_request)
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: write  # Required for auto-merge functionality

    steps:
      - name: Checkout Code
        uses: actions/checkout@v6

      - name: Run Owners File Action
        uses: coreos/owners-file-action@v1.0
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          owners-file: "OWNERS"
        env:
          MERGE_STRATEGY: merge  # Optional: merge (default), squash, or rebase
```

## OWNERS File Format

Create an `OWNERS` file in your repository root:

```yaml
approvers:
  - username1
  - username2

reviewers:
  - username3
  - username4
```

- **approvers**: Users who can use `/approve` to approve PRs
- **reviewers**: Users who can use `/lgtm` to indicate PR looks good

## Commands

Comment on a pull request with these commands:

- `/lgtm` - Reviewers can mark PR as "looks good to me"
- `/lgtm cancel` - Cancel a previous `/lgtm`
- `/approve` - Approvers can approve the PR
- `/approve cancel` - Cancel a previous `/approve`
- `/hold` - Approvers can place a hold on the PR to prevent auto-merge
- `/hold cancel` - Remove the hold

## Auto-Merge

The action automatically merges PRs when all conditions are met:

- ✅ PR has the `lgtm` label (added by a reviewer)
- ✅ PR has the `approved` label (added by an approver)
- ✅ PR does NOT have the `hold` label

The merge will happen automatically after any comment command or label event. You can control the merge strategy using the `MERGE_STRATEGY` environment variable:

- `merge` (default) - Creates a merge commit
- `squash` - Squashes all commits into one
- `rebase` - Rebases commits onto the base branch

## Label Protection

The action automatically protects the `lgtm` and `approved` labels from unauthorized manual changes:

- **Manual label additions**: If someone tries to manually add these labels (bypassing the OWNERS file authorization), the bot will automatically remove them
- **Manual label removals**: If someone tries to manually remove these labels (bypassing the cancel commands), the bot will automatically re-add them
- **Bot-only management**: Only the bot itself can manage these labels through the `/lgtm`, `/approve`, and their cancel commands

This ensures that the OWNERS file authorization process cannot be bypassed by directly manipulating labels through the GitHub UI.
