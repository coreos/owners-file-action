# Owners Bot Action

A GitHub Action that handles `/lgtm` and `/approve` commands on pull requests based on an OWNERS file.

## Features

- Responds to `/lgtm` and `/approve` comments on pull requests
- Validates commenters against an OWNERS file
- Automatically adds labels to PRs based on approvals

## Usage

Create a workflow file (e.g., `.github/workflows/owners-bot.yml`):

```yaml
name: Owners Bot

on:
  issue_comment:
    types: [created]

jobs:
  handle-comment:
    if: ${{ github.event.issue.pull_request }}
    runs-on: ubuntu-latest
    permissions:
      pull-requests: write
      contents: read

    steps:
      - name: Checkout Code
        uses: actions/checkout@v6

      - name: Run Owners Bot
        uses: acardace/owners-bot-action@v1.0
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          owners-file: "OWNERS"
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
