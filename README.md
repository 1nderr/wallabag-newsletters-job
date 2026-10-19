# Wallabag Newsletters Job

This is a scheduled job I run to sync Wallabag with the newsletters I receive via email. I run it every 1 minute. It will look at all of my UNREAD emails with the "newsletters" label and then send their contents to Wallabag. It will also mark those emails as read so that they do not get picked up on future runs.

## Prerequisites

- `google_creds.json`: credentials file from Google Auth Platform
- `wallabag_creds.json`: a file containing the following from Wallabag

```json
{
  "client_id": "",
  "client_secret": "",
  "username": "",
  "password": ""
}
```

## Installation

`uv sync`

## Usage

`uv run wallabag-newsletters-job`
