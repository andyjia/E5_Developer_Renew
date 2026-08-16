# -*- coding: UTF-8 -*-
import argparse
import os
import sys
from pathlib import Path

import requests as req
# Please register your Azure Application first, and grant it with the mandatory permissions below:
# files:	Files.Read.All、Files.ReadWrite.All、Sites.Read.All、Sites.ReadWrite.All
# user:	    User.Read.All、User.ReadWrite.All、Directory.Read.All、Directory.ReadWrite.All
# mail:     Mail.Read、Mail.ReadWrite、MailboxSettings.Read、MailboxSettings.ReadWrite
# Remember to Click "Grant admin consent for <your tenant>" in the "API Permissions" page.

# The rotated refresh token is stored next to this script.
# refresh_token.txt is gitignored, see .gitignore.
path = Path(__file__).resolve().parent / 'refresh_token.txt'

api_list = [
    'https://graph.microsoft.com/v1.0/me/drive/root',
    'https://graph.microsoft.com/v1.0/me/drive',
    'https://graph.microsoft.com/v1.0/drive/root',
    'https://graph.microsoft.com/v1.0/users',
    'https://graph.microsoft.com/v1.0/me/messages',
    'https://graph.microsoft.com/v1.0/me/mailFolders/inbox/messageRules',
    'https://graph.microsoft.com/v1.0/me/mailFolders/Inbox/messages/delta',
    'https://graph.microsoft.com/v1.0/me/drive/root/children',
    'https://api.powerbi.com/v1.0/myorg/apps',
    'https://graph.microsoft.com/v1.0/me/mailFolders',
    'https://graph.microsoft.com/v1.0/me/outlook/masterCategories'
]

# Token endpoint and request settings
TOKEN_ENDPOINT = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'
REDIRECT_URI = 'http://localhost:53682/'
REQUEST_TIMEOUT = 30


def gettoken(client_id, client_secret, refresh_token):
    """Refresh the access token and persist the rotated refresh token.

    Returns a (access_token, new_refresh_token) tuple. Microsoft does not
    revoke the old refresh token when a new one is issued, but the client
    is expected to discard it and use the new one, so the caller MUST use
    the returned refresh token for the next refresh.
    """
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': REDIRECT_URI,
    }
    try:
        response = req.post(TOKEN_ENDPOINT, data=data, headers=headers, timeout=REQUEST_TIMEOUT)
    except req.RequestException as exc:
        raise RuntimeError('Failed to reach the token endpoint: %s' % exc) from exc
    if response.status_code != 200:
        raise RuntimeError('Failed to refresh token: HTTP %s %s' % (response.status_code, response.text))
    try:
        jsontxt = response.json()
    except ValueError as exc:
        raise RuntimeError('Token endpoint returned a non-JSON response: %s' % response.text[:200]) from exc
    if not isinstance(jsontxt, dict):
        raise RuntimeError('Token endpoint returned an unexpected response shape: %s' % response.text[:200])
    access_token = jsontxt['access_token']
    # Some responses do not rotate the refresh token; keep the old one then
    # (also guards against a null refresh_token field in the response).
    new_refresh_token = jsontxt.get('refresh_token') or refresh_token
    path.write_text(new_refresh_token, encoding='utf-8')
    return access_token, new_refresh_token


def main():
    parser = argparse.ArgumentParser(description='Generate the access token from the refresh token to call the Microsoft Graph API.')
    # Credentials may be passed on the command line, but preferably via the
    # environment (AZURE_CLIENT_ID / AZURE_CLIENT_SECRET / REFRESH_TOKEN) so
    # they never appear in the process list or shell history.
    parser.add_argument('-i', '--id', type=str, help='Application Client ID (or set AZURE_CLIENT_ID)')
    parser.add_argument('-s', '--secret', type=str, help='Client Secret (or set AZURE_CLIENT_SECRET)')
    parser.add_argument('-r', '--refresh', type=str, help='Refresh Token (or set REFRESH_TOKEN)')
    parser.add_argument('-t', '--times', type=int, default=5, help='Number of times to refresh the token and call the APIs (default: 5)')
    args = parser.parse_args()

    client_id = args.id or os.environ.get('AZURE_CLIENT_ID')
    client_secret = args.secret or os.environ.get('AZURE_CLIENT_SECRET')
    refresh_token = args.refresh or os.environ.get('REFRESH_TOKEN')
    if not (client_id and client_secret and refresh_token):
        parser.error('Client ID, client secret and refresh token are required (via args or environment variables).')

    call_count = 0
    try:
        for _ in range(args.times):
            # Use the freshly rotated refresh token on every iteration.
            access_token, refresh_token = gettoken(client_id, client_secret, refresh_token)
            headers = {
                'Authorization': 'Bearer ' + access_token,
                'Content-Type': 'application/json',
            }
            for api in api_list:
                try:
                    response = req.get(api, headers=headers, timeout=REQUEST_TIMEOUT)
                    if response.status_code == 200:
                        call_count += 1
                        print(f"Call {api} successfully")
                    else:
                        # Include a snippet of the body to help debug permission issues.
                        detail = response.text[:200].replace('\n', ' ')
                        print(f"Call {api} failed: HTTP {response.status_code} - {detail}")
                except req.RequestException as exc:
                    print(f"Call {api} error: {exc}")
    except RuntimeError as exc:
        print(f"::error:: {exc}", file=sys.stderr)
        sys.exit(1)

    print("End of the test, the total number of successful calls is:", call_count)
    if call_count == 0:
        print("::warning:: No API calls succeeded. The refresh token was still rotated, but please check the API permissions.", file=sys.stderr)


if __name__ == '__main__':
    main()
