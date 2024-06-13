import os
import pickle
import datetime
import pytz
import logging
import time
import json
from flask import Flask, request, jsonify, Response
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# 定义多个授权范围
SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/calendar.events.readonly',
    'https://www.googleapis.com/auth/calendar.events'
]

# 配置日志记录
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(levelname)s %(message)s')

app = Flask(__name__)

def get_credentials():
    creds = None
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            try:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=8090)
            except Exception as e:
                logging.error(f"Local server authorization failed: {e}")
                logging.info("Switching to manual authorization...")
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
                auth_url, _ = flow.authorization_url(prompt='consent')

                logging.info(f'Please visit this URL on a device with a web browser: {auth_url}')
                code = input('Enter the authorization code: ')
                flow.fetch_token(code=code)
                creds = flow.credentials
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)
    return creds

def build_service():
    creds = get_credentials()
    service = build('calendar', 'v3', credentials=creds)
    return service

@app.route('/events', methods=['POST'])
def get_events():
    service = build_service()
    data = request.json
    now = datetime.datetime.now(pytz.timezone('Asia/Shanghai')).isoformat()
    time_min = data.get('timeMin', now)
    time_max = data.get('timeMax', None)
    events_result = service.events().list(calendarId='primary', timeMin=time_min,
                                          timeMax=time_max, maxResults=10, singleEvents=True,
                                          orderBy='startTime').execute()
    events = events_result.get('items', [])
    response_json = json.dumps({'items': events}, ensure_ascii=False)
    return Response(response_json, content_type='application/json')

@app.route('/events/create', methods=['POST'])
def create_event():
    service = build_service()
    event_data = request.json
    event = service.events().insert(calendarId='primary', body=event_data).execute()
    response_json = json.dumps({'event': event}, ensure_ascii=False)
    return Response(response_json, content_type='application/json')

@app.route('/events/update', methods=['POST'])
def update_event():
    service = build_service()
    data = request.json
    event_id = data.get('eventId')
    event_data = {
        key: value for key, value in data.items() if key != 'eventId'
    }
    updated_event = service.events().update(calendarId='primary', eventId=event_id, body=event_data).execute()
    response_json = json.dumps({'event': updated_event}, ensure_ascii=False)
    return Response(response_json, content_type='application/json')

@app.route('/events/delete', methods=['POST'])
def delete_event():
    service = build_service()
    data = request.json
    event_id = data.get('eventId')
    service.events().delete(calendarId='primary', eventId=event_id).execute()
    response_json = json.dumps({'status': 'Event deleted'}, ensure_ascii=False)
    return Response(response_json, content_type='application/json')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4045, debug=True)  # 确保监听所有网络接口