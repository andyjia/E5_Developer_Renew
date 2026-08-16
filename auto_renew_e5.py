# -*- coding: UTF-8 -*-
import argparse
import sys

import requests as req
# Please register your Azure Application first, and grant it with the mandatory permissions below:
# files:	Files.Read.All、Files.ReadWrite.All、Sites.Read.All、Sites.ReadWrite.All
# user:	    User.Read.All、User.ReadWrite.All、Directory.Read.All、Directory.ReadWrite.All
# mail:     Mail.Read、Mail.ReadWrite、MailboxSettings.Read、MailboxSettings.ReadWrite
# Remember to Click "Grant admin consent for <your tenant>" in the "API Permissions" page.

path = sys.path[0]+r'/refresh_token.txt'
call_count = 0
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

# Get the access token from microsoft graph api and write the new refresh token to the file.
def gettoken(client_id, client_secret, refresh_token):
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}
    data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': REDIRECT_URI,
    }
    response = req.post(TOKEN_ENDPOINT, data=data, headers=headers, timeout=REQUEST_TIMEOUT)
    if response.status_code != 200:
        raise RuntimeError('Failed to refresh token: HTTP %s %s' % (response.status_code, response.text))
    jsontxt = response.json()
    refresh_token = jsontxt['refresh_token']
    access_token = jsontxt['access_token']
    with open(path, 'w+') as f:
        f.write(refresh_token)
    return access_token

def main():
    parser = argparse.ArgumentParser(description='Generate the access token from the refresh token to call the Microsoft Graph API.')
    parser.add_argument('-i', '--id', type=str, help='Application Client ID', required=True)
    parser.add_argument('-s', '--secret', type=str, help='Client Secret', required=True)
    parser.add_argument('-r', '--refresh', type=str, help='Refresh Token', required=True)
    parser.add_argument('-t', '--times', type=int, default=5, help='Number of times to refresh the token and call the APIs (default: 5)')
    args = parser.parse_args()

    global call_count
    try:
        for _ in range(args.times):
            access_token = gettoken(args.id, args.secret, args.refresh)
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
                        print(f"Call {api} failed: HTTP {response.status_code}")
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
