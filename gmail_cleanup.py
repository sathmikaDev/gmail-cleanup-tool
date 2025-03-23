import os
import datetime
import pickle
import tkinter as tk
from tkinter import messagebox, scrolledtext
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

# Scopes for Gmail API (full access for deletion)
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


def clean_old_emails(service, log_output, status_label):
    try:
        status_label.config(text="Cleaning old emails...", fg="blue")
        app.update()  # Force GUI update
        log_output("🔍 Searching for emails older than 30 days...")
        days = 30
        date_limit = datetime.datetime.now() - datetime.timedelta(days=days)
        query = f"before:{date_limit.strftime('%Y/%m/%d')}"
        results = service.users().messages().list(userId='me', q=query, maxResults=100).execute()
        messages = results.get('messages', [])
        if not messages:
            log_output("✅ No old emails found.")
            status_label.config(text="Idle", fg="black")
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
        status_label.config(text="Idle", fg="black")
    except HttpError as e:
        log_output(f"❌ Error archiving emails: {str(e)}")
        status_label.config(text="Error occurred", fg="red")


def delete_spam(service, log_output, status_label):
    try:
        status_label.config(text="Deleting spam...", fg="blue")
        app.update()  # Force GUI update
        log_output("🧹 Looking for spam emails to delete...")
        spam = service.users().messages().list(userId='me', labelIds=['SPAM'], maxResults=100).execute()
        messages = spam.get('messages', [])
        if not messages:
            log_output("✅ No spam emails found.")
            status_label.config(text="Idle", fg="black")
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
            batch.add(service.users().messages().delete(userId='me', id=msg_id), callback=callback)

        batch.execute()
        log_output(f"✅ Processed {len(messages)} spam emails, successfully deleted {deleted_count}.")
        status_label.config(text="Idle", fg="black")
    except HttpError as e:
        log_output(f"❌ Error deleting spam: {str(e)}")
        status_label.config(text="Error occurred", fg="red")


def start_cleanup(service, log_output, status_label):
    try:
        status_label.config(text="Authenticating...", fg="blue")
        app.update()  # Force GUI update
        log_output("🔐 Authenticating with Gmail...")
        log_output("✅ Authentication successful!")
        clean_old_emails(service, log_output, status_label)
        delete_spam(service, log_output, status_label)
        messagebox.showinfo("Done", "Email cleanup completed successfully!")
        status_label.config(text="Idle", fg="black")
    except Exception as e:
        messagebox.showerror("Error", f"Cleanup failed: {str(e)}")
        status_label.config(text="Error occurred", fg="red")


def log_output(msg):
    output_text.config(state=tk.NORMAL)
    output_text.insert(tk.END, msg + '\n')
    output_text.see(tk.END)
    output_text.config(state=tk.DISABLED)


def clear_log():
    output_text.config(state=tk.NORMAL)  # Enable the widget
    output_text.delete(1.0, tk.END)  # Clear all text
    output_text.config(state=tk.DISABLED)  # Disable it again


# Build enhanced GUI
app = tk.Tk()
app.title("📧 Gmail Cleanup Tool")
app.geometry("600x450")
app.resizable(False, False)

# Header Frame
header_frame = tk.Frame(app, bg="#f0f0f0")
header_frame.pack(fill=tk.X, pady=10)
tk.Label(header_frame, text="Gmail Inbox Cleanup", font=("Helvetica", 18, "bold"), bg="#f0f0f0").pack(pady=5)

# Status Frame
status_frame = tk.Frame(app)
status_frame.pack(fill=tk.X, padx=10, pady=5)
tk.Label(status_frame, text="Status:", font=("Arial", 12, "bold")).pack(side=tk.LEFT)
status_label = tk.Label(status_frame, text="Idle", font=("Arial", 12), fg="black")
status_label.pack(side=tk.LEFT, padx=5)

# Buttons Frame
button_frame = tk.Frame(app)
button_frame.pack(pady=10)
tk.Button(button_frame, text="Start Cleanup",
          command=lambda: start_cleanup(service, log_output, status_label),
          bg="#4CAF50", fg="white", font=("Arial", 12), width=15, height=2).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="Clear Log",
          command=clear_log,  # Updated to use the new function
          bg="#2196F3", fg="white", font=("Arial", 12), width=15, height=2).pack(side=tk.LEFT, padx=5)
tk.Button(button_frame, text="Quit",
          command=app.quit,
          bg="#f44336", fg="white", font=("Arial", 12), width=15, height=2).pack(side=tk.LEFT, padx=5)

# Output Text Area
output_text = scrolledtext.ScrolledText(app, wrap=tk.WORD, height=15, state=tk.DISABLED, font=("Arial", 10))
output_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

# Footer Frame (optional info)
footer_frame = tk.Frame(app, bg="#f0f0f0")
footer_frame.pack(fill=tk.X, pady=5)
tk.Label(footer_frame, text="v1.0 | Powered by Gmail API", font=("Arial", 8), bg="#f0f0f0").pack()

# Initialize Gmail service
try:
    service = gmail_auth(log_output)
except Exception as e:
    messagebox.showerror("Error", f"Initialization failed: {str(e)}")
    app.quit()

app.mainloop()