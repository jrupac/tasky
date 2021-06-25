#!/usr/bin/env python3

from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession
from googleapiclient.discovery import build

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

import os
import json


def get_credentials():

    CLIENT_SECRET_FILE = 'client_id.json'
    SCOPES = ['https://www.googleapis.com/auth/tasks']

    credentials_path = 'user_token'

    if os.path.exists(credentials_path):
        # expect these to be valid. may expire at some point, but should be refreshed by google api client...
        return Credentials.from_authorized_user_file(credentials_path, scopes=SCOPES)
    else:
        flow = InstalledAppFlow.from_client_secrets_file(
        CLIENT_SECRET_FILE,
        scopes=SCOPES,
        redirect_uri='urn:ietf:wg:oauth:2.0:oob')

        credentials = flow.run_local_server()

        credentials_as_dict = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'id_token': credentials.id_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret
        }

        with open(credentials_path, 'w') as file:
            file.write(json.dumps(credentials_as_dict))

        return credentials

print(get_credentials())
