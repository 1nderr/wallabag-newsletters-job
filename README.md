# Wallabag Newsletters Job

This is a scheduled job I run to sync Wallabag with the newsletters I receive via email. It will look at emails from the past day and post them to Wallabag. It will also send you an email summarizing what it posted and if there were any errors.

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
