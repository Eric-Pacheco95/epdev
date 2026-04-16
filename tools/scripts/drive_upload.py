"""
One-shot Google Drive upload using local MCP OAuth credentials.
Re-authenticates via browser if tokens are expired.
Usage: python drive_upload.py <file_path> <file_name> <folder_id>
"""
import json, sys, os, requests
from pathlib import Path

TOKENS_PATH = Path.home() / '.config' / 'google-drive-mcp' / 'tokens.json'
KEYS_PATH   = Path.home() / '.config' / 'google-drive-mcp' / 'gcp-oauth.keys.json'
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_creds():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    with open(KEYS_PATH) as f:
        keys = json.load(f)
    client_info = keys.get('installed') or keys.get('web', {})

    try:
        with open(TOKENS_PATH) as f:
            tok = json.load(f)
        creds = Credentials(
            token=tok.get('access_token'),
            refresh_token=tok.get('refresh_token'),
            token_uri='https://oauth2.googleapis.com/token',
            client_id=client_info['client_id'],
            client_secret=client_info['client_secret'],
        )
        if creds.refresh_token:
            creds.refresh(Request())
            return creds
    except Exception as e:
        print(f"Token refresh failed ({e}), launching browser auth...")

    # Re-auth via browser
    from google_auth_oauthlib.flow import InstalledAppFlow
    flow = InstalledAppFlow.from_client_config(keys, SCOPES)
    creds = flow.run_local_server(port=0)

    # Save refreshed tokens back
    tok_data = {
        'access_token':  creds.token,
        'refresh_token': creds.refresh_token,
        'token_type':    'Bearer',
        'scope':         ' '.join(creds.scopes or SCOPES),
        'expiry_date':   int(creds.expiry.timestamp() * 1000) if creds.expiry else 0,
    }
    with open(TOKENS_PATH, 'w') as f:
        json.dump(tok_data, f, indent=2)
    print("Tokens saved.")
    return creds


def upload(file_path, file_name, folder_id):
    creds = get_creds()
    mime = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    metadata = {'name': file_name, 'parents': [folder_id]}

    with open(file_path, 'rb') as f:
        content = f.read()

    print(f"Uploading {len(content)/1024/1024:.1f} MB...")
    resp = requests.post(
        'https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart&fields=id,name,webViewLink',
        headers={'Authorization': f'Bearer {creds.token}'},
        files={
            'metadata': ('metadata', json.dumps(metadata), 'application/json'),
            'file': (file_name, content, mime),
        }
    )
    result = resp.json()
    if 'id' in result:
        print(f"SUCCESS")
        print(f"  File ID:  {result['id']}")
        print(f"  Name:     {result.get('name')}")
        print(f"  Link:     {result.get('webViewLink', 'https://drive.google.com/file/d/' + result['id'])}")
    else:
        print(f"ERROR: {json.dumps(result, indent=2)}")


if __name__ == '__main__':
    if len(sys.argv) != 4:
        print("Usage: python drive_upload.py <file_path> <file_name> <folder_id>")
        sys.exit(1)
    upload(sys.argv[1], sys.argv[2], sys.argv[3])
