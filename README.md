# Gmail Cleanup Tool
A Python script with a Tkinter GUI to clean up old emails and delete spam from your Gmail account.

## Requirements
- Python 3.x
- `google-auth-oauthlib`, `google-auth-httplib2`, `google-api-python-client`
- A `credentials.json` file from Google Cloud Console (not included)

## Setup
1. Install dependencies: `pip install google-auth-oauthlib google-auth-httplib2 google-api-python-client`
2. Obtain `credentials.json` from Google Cloud Console (see instructions below).
3. Run the script: `python gmail_cleanup.py`

## Notes
- Do not commit `credentials.json` or `token.pickle` to version control.