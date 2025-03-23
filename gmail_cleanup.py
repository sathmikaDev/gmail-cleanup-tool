import os
import datetime
import pickle
import tkinter as tk
from tkinter import messagebox
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://mail.google.com/']


def gmail_auth(log_output):
    creds = None
    try:
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists('credentials.json'):
                    raise FileNotFoundError("credentials.json not found.")
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)
        return build('gmail', 'v1', credentials=creds)
    except Exception as e:
        log_output(f"❌ Authentication error: {str(e)}")
        raise


def clean_old_emails(service, log_output):
    try:
        log_output("🔍 Searching for emails older than 30 days...")
        days = 30
        date_limit = datetime.datetime.now() - datetime.timedelta(days=days)
        query = f"before:{date_limit.strftime('%Y/%m/%d')}"
        results = service.users().messages().list(userId='me', q=query, maxResults=100).execute()
        messages = results.get('messages', [])
        if not messages:
            log_output("✅ No old emails found.")
            return
        batch = service.new_batch_http_request()
        for msg in messages:
            msg_id = msg['id']
            batch.add(service.users().messages().modify(
                userId='me',
                id=msg_id,
                body={'removeLabelIds': ['INBOX']}
            ))
            log_output(f"📦 Queued email ID: {msg_id} for archiving")
        batch.execute()
        log_output(f"✅ Archived {len(messages)} emails older than {days} days.")
    except HttpError as e:
        log_output(f"❌ Error archiving emails: {str(e)}")


def delete_spam(service, log_output):
    try:
        log_output("🧹 Looking for spam emails to delete...")
        spam = service.users().messages().list(userId='me', labelIds=['SPAM'], maxResults=100).execute()
        messages = spam.get('messages', [])
        if not messages:
            log_output("✅ No spam emails found.")
            return

        batch = service.new_batch_http_request()
        deleted_count = 0

        def callback(request_id, response, exception):
            nonlocal deleted_count
            if exception is not None:
                log_output(f"❌ Failed to delete email ID {request_id}: {str(exception)}")
            else:
                log_output(f"🗑️ Successfully deleted spam email ID: {request_id}")
                deleted_count += 1

        for msg in messages:
            msg_id = msg['id']
            # Use delete directly
            batch.add(service.users().messages().delete(userId='me', id=msg_id), callback=callback)

        batch.execute()
        log_output(f"✅ Processed {len(messages)} spam emails, successfully deleted {deleted_count}.")

        # If some emails remain, try moving to trash first
        if deleted_count < len(messages):
            log_output("⚠️ Some emails weren’t deleted directly. Attempting trash method...")
            remaining = service.users().messages().list(userId='me', labelIds=['SPAM'], maxResults=100).execute()
            remaining_msgs = remaining.get('messages', [])
            if remaining_msgs:
                batch_trash = service.new_batch_http_request()
                for msg in remaining_msgs:
                    msg_id = msg['id']
                    # Move to trash first
                    batch_trash.add(service.users().messages().trash(userId='me', id=msg_id), callback=callback)
                batch_trash.execute()
                # Then permanently delete from trash
                trash = service.users().messages().list(userId='me', labelIds=['TRASH'], maxResults=100).execute()
                trash_msgs = trash.get('messages', [])
                if trash_msgs:
                    batch_delete = service.new_batch_http_request()
                    for msg in trash_msgs:
                        msg_id = msg['id']
                        batch_delete.add(service.users().messages().delete(userId='me', id=msg_id), callback=callback)
                    batch_delete.execute()
                log_output(f"✅ Final cleanup: {deleted_count} spam emails deleted.")
    except HttpError as e:
        log_output(f"❌ Error deleting spam: {str(e)}")


def start_cleanup():
    try:
        log_output("🔐 Authenticating with Gmail...")
        service = gmail_auth(log_output)
        log_output("✅ Authentication successful!")
        clean_old_emails(service, log_output)
        delete_spam(service, log_output)
        messagebox.showinfo("Done", "Email cleanup completed successfully!")
    except Exception as e:
        messagebox.showerror("Error", f"Cleanup failed: {str(e)}")


def log_output(msg):
    output_text.config(state=tk.NORMAL)
    output_text.insert(tk.END, msg + '\n')
    output_text.see(tk.END)
    output_text.config(state=tk.DISABLED)


app = tk.Tk()
app.title("📧 Gmail Cleanup Tool")
app.geometry("600x400")
app.resizable(False, False)

tk.Label(app, text="Gmail Inbox Cleanup", font=("Helvetica", 16, "bold")).pack(pady=10)
tk.Button(app, text="Start Cleanup", command=start_cleanup, bg="#4CAF50", fg="white", font=("Arial", 12),
          width=20, height=2).pack(pady=10)
output_text = tk.Text(app, wrap=tk.WORD, height=15, state=tk.DISABLED)
output_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

app.mainloop()