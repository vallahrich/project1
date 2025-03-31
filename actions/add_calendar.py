import os.path
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pickle

SCOPES = ['https://www.googleapis.com/auth/calendar.events']

class ActionAddCalendarEvent(Action):
    def name(self) -> Text:
        return "action_add_calendar_event"

    def _get_calendar_service(self):
        creds = None
        if os.path.exists('token.pickle'):
            with open('token.pickle', 'rb') as token:
                creds = pickle.load(token)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', SCOPES)
                creds = flow.run_local_server(port=8090)
            with open('token.pickle', 'wb') as token:
                pickle.dump(creds, token)

        return build('calendar', 'v3', credentials=creds)

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get event details from slots
        event_title = tracker.get_slot("event_title")
        event_date = tracker.get_slot("event_date")
        event_time = tracker.get_slot("event_time")
        event_duration = tracker.get_slot("event_duration") or 60  # Default: 60 minutes

        try:
            # Parse date and time
            start_time = datetime.strptime(f"{event_date} {event_time}", "%Y-%m-%d %H:%M")
            end_time = start_time + timedelta(minutes=int(event_duration))

            # Create the event
            event = {
                'summary': event_title,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': 'Europe/Berlin',
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': 'Europe/Berlin',
                },
            }

            # Add event to calendar
            service = self._get_calendar_service()
            event = service.events().insert(calendarId='primary', body=event).execute()

            # Success response
            dispatcher.utter_message(
                text=f"I have created the event '{event_title}' for {event_date} at {event_time}.")

        except Exception as e:
            # Error handling
            dispatcher.utter_message(
                text=f"Sorry, I couldn't create the event. Error: {str(e)}")

        return [] 