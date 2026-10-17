import base64
import json
import os.path
import uuid
from datetime import datetime, timedelta
from email.message import EmailMessage

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
GOOGLE_CREDS_FILE = "google_creds.json"
GOOGLE_TOKEN_FILE = "google_token.json"
WALLABAG_CREDS_FILE = "wallabag_creds.json"
WALLABAG_URL = "https://wallabag.indervir.dev"
WALLABAG_TOKEN = None
SUBJECTS: list[str] = []
ERRORS: list[str] = []


def get_google_token():
    creds = None
    if os.path.exists(GOOGLE_TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(GOOGLE_TOKEN_FILE, SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(GOOGLE_CREDS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(GOOGLE_TOKEN_FILE, "w") as token:
            token.write(creds.to_json())

    return creds


def get_wallabag_token():
    with open(WALLABAG_CREDS_FILE, "r", encoding="utf-8") as file:
        data = json.load(file)
        payload = {
            "grant_type": "password",
            "client_id": data["client_id"],
            "client_secret": data["client_secret"],
            "username": data["username"],
            "password": data["password"],
        }

        token_url = f"{WALLABAG_URL.rstrip('/')}/oauth/v2/token"
        response = requests.post(token_url, data=payload)
        if response.status_code == 200:
            token_data = response.json()
            access_token = token_data.get("access_token")
            return access_token
        else:
            raise requests.RequestException(response.content)


def get_newsletters():
    google_token = get_google_token()

    global WALLABAG_TOKEN
    WALLABAG_TOKEN = get_wallabag_token()

    service = None
    try:
        before = datetime.now()
        after = before - timedelta(hours=3)

        service = build("gmail", "v1", credentials=google_token)
        results = (
            service.users()
            .messages()
            .list(
                userId="me",
                q=f"label:Newsletters before:{int(before.timestamp())} after:{int(after.timestamp())}",
            )
            .execute()
        )
        messages = results.get("messages", [])
        if not messages:
            return

        batch = service.new_batch_http_request(callback=process_message)
        for message in messages:
            batch.add(service.users().messages().get(userId="me", id=message["id"]))
        batch.execute()

        newsletters_sent = "\n- ".join([""] + SUBJECTS)
        errors = "\n- ".join([""] + ERRORS)
        summary = newsletters_sent + "\n" + errors
        send_email(service, summary)

    except Exception as error:
        send_email(service, error)


def process_message(request_id, response, exception):
    if exception is not None:
        ERRORS.append(f"Error processing message {request_id}: {exception}")
        return

    payload = response.get("payload", {})
    headers = payload.get("headers", [])

    subject = "No Subject"
    for header in headers:
        if header["name"].lower() == "subject" and header["value"] != "":
            subject = header["value"]
            break
    SUBJECTS.append(subject)

    body = "No Body"
    if "parts" in payload:
        body = parse_multipart_message(payload, "text/html")
        if not body:
            body = parse_multipart_message(payload, "text/plain")
    else:
        data = payload.get("body", {}).get("data")
        if data:
            body = base64.urlsafe_b64decode(data).decode("utf-8")

    send_entry_to_wallabag(subject, body)


def parse_multipart_message(payload, mimeType):
    for part in payload["parts"]:
        if part.get("mimeType") == mimeType:
            data = part.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8")
    return None


def send_entry_to_wallabag(title, content):
    payload = {
        "url": f"http://www.indervir.dev/{uuid.uuid4()}.html",
        "title": title,
        "content": content,
    }

    headers = {
        "Authorization": f"Bearer {WALLABAG_TOKEN}",
        "Content-Type": "application/json",
    }

    token_url = f"{WALLABAG_URL.rstrip('/')}/api/entries"
    response = requests.post(token_url, json=payload, headers=headers)
    if response.status_code != 200:
        raise requests.RequestException(response.content)


def send_email(service, content):
    message = EmailMessage()
    message.set_content(content)
    message["To"] = "<INSERT_EMAIL>@gmail.com"
    message["From"] = "<INSERT_EMAIL>@gmail.com"
    message["Subject"] = "Wallabag Newsletter Job"
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

    send_request = (
        service.users().messages().send(userId="me", body={"raw": raw_message})
    )
    return send_request.execute()


def main():
    get_newsletters()


if __name__ == "__main__":
    main()
