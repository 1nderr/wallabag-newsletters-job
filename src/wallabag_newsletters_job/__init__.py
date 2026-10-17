import base64
import os.path
from datetime import datetime, timedelta

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

SUBJECTS = []
ERRORS = []


def get_creds():
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    return creds


def get_newsletters():
    creds = get_creds()
    try:
        before = datetime.now()
        after = before - timedelta(hours=3)

        service = build("gmail", "v1", credentials=creds)
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
            print("No messages found.")
            return

        batch = service.new_batch_http_request(callback=process_message)
        for message in messages:
            batch.add(service.users().messages().get(userId="me", id=message["id"]))
        batch.execute()
        # TODO: send summary email

    except HttpError as error:
        # TODO: send email on error
        print(f"An error occurred: {error}")


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


def parse_multipart_message(payload, mimeType):
    for part in payload["parts"]:
        if part.get("mimeType") == mimeType:
            data = part.get("body", {}).get("data")
            if data:
                return base64.urlsafe_b64decode(data).decode("utf-8")
    return None


def main():
    get_newsletters()


if __name__ == "__main__":
    main()
