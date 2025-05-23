"""
New actions for OpenAI fallback, medication reminders, and help tracking.
"""
import os
import logging
import requests
import json
from typing import Any, Text, Dict, List
from datetime import datetime, timedelta
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet, FollowupAction
from rasa_sdk.executor import CollectingDispatcher

# Google Calendar imports
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

class ActionOpenAIFallback(Action):
    """Call OpenAI API for general questions."""
    
    def name(self) -> Text:
        return "action_openai_fallback"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Call OpenAI API to generate a response for general questions.
        """
        try:
            # Get the user's message
            user_message = tracker.latest_message.get("text", "")
            
            # Get OpenAI API key
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                dispatcher.utter_message(text="I'm having trouble connecting to my knowledge base. Please try again later.")
                return []
            
            # Prepare the prompt
            prompt = f"""
            You are a helpful assistant. Answer the following question concisely and accurately.
            If you're not sure about something, say so.
            
            User question: {user_message}
            """
            
            # Call OpenAI API
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-2024-11-20",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.7
                },
                timeout=10
            )
            
            # Parse response
            response_data = response.json()
            answer = response_data["choices"][0]["message"]["content"].strip()
            
            dispatcher.utter_message(text=answer)
            
            return [SlotSet("openai_response", answer)]
            
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            dispatcher.utter_message(text="I'm sorry, I couldn't process your question. Please try again.")
            return []

class ActionIncrementHelpCount(Action):
    """Increment the help counter when user says 'hilfe'."""
    
    def name(self) -> Text:
        return "action_increment_help_count"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Increment help count.
        """
        current_count = tracker.get_slot("help_count") or 0
        new_count = current_count + 1
        
        logger.info(f"Help count incremented to: {new_count}")
        
        return [SlotSet("help_count", new_count)]

class ActionCheckHelpThreshold(Action):
    """Check if help has been said twice and trigger emergency if so."""
    
    def name(self) -> Text:
        return "action_check_help_threshold"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Check help count and trigger emergency action if threshold reached.
        """
        help_count = tracker.get_slot("help_count") or 0
        
        if help_count >= 2:
            # Reset count and trigger emergency flow
            logger.info("Help threshold reached, triggering emergency action")
            # Trigger the existing emergency_twillio action directly
            return [
                SlotSet("help_count", 0),
                FollowupAction("emergency_twillio")
            ]
        else:
            # First time saying help - just acknowledge
            dispatcher.utter_message(response="utter_first_help")
            return []

class ActionCreateMedicationReminder(Action):
    """Create a medication reminder in Google Calendar."""
    
    def name(self) -> Text:
        return "action_create_medication_reminder"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Create a recurring event in Google Calendar for medication reminders.
        """
        try:
            # Get slot values
            medication = tracker.get_slot("medication_name")
            time_str = tracker.get_slot("reminder_time")
            date_str = tracker.get_slot("reminder_date")
            frequency = tracker.get_slot("reminder_frequency")
            
            # Initialize Google Calendar API
            service = self._get_calendar_service()
            if not service:
                logger.error("Failed to initialize Google Calendar service")
                return [SlotSet("return_value", "failed")]
            
            # Parse date and time
            reminder_datetime = self._parse_datetime(date_str, time_str)
            
            # Create the event
            event = {
                'summary': f'Medication Reminder: {medication}',
                'description': f'Time to take your {medication}',
                'start': {
                    'dateTime': reminder_datetime.isoformat(),
                    'timeZone': 'Europe/Copenhagen',  # Based on user location
                },
                'end': {
                    'dateTime': (reminder_datetime + timedelta(minutes=15)).isoformat(),
                    'timeZone': 'Europe/Copenhagen',
                },
                'recurrence': self._get_recurrence_rule(frequency),
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 0},
                        {'method': 'notification', 'minutes': 0},
                    ],
                },
            }
            
            # Insert the event
            event = service.events().insert(calendarId='primary', body=event).execute()
            logger.info(f'Event created: {event.get("htmlLink")}')
            
            return [SlotSet("return_value", "success")]
            
        except Exception as e:
            logger.error(f"Error creating medication reminder: {e}")
            return [SlotSet("return_value", "failed")]
    
    def _get_calendar_service(self):
        """Initialize Google Calendar service."""
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        
        creds = None
        token_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "credentials",
            "gcal_token.json"
        )
        credentials_path = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_PATH") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "credentials",
            "gcal_credentials.json"
        )
        
        # Token loading and refresh logic similar to email client
        if os.path.exists(token_path):
            try:
                with open(token_path, 'r') as token:
                    creds = Credentials.from_authorized_user_info(
                        json.load(token),
                        SCOPES
                    )
            except Exception as e:
                logger.error(f"Error loading token: {e}")
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    logger.error(f"Error refreshing token: {e}")
                    creds = None
            
            if not creds:
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                    
                    # Save the credentials
                    with open(token_path, 'w') as token:
                        json.dump(json.loads(creds.to_json()), token)
                except Exception as e:
                    logger.error(f"Error during OAuth flow: {e}")
                    return None
        
        try:
            return build('calendar', 'v3', credentials=creds)
        except Exception as e:
            logger.error(f"Failed to build Calendar service: {e}")
            return None
    
    def _parse_datetime(self, date_str: str, time_str: str) -> datetime:
        """Parse date and time strings into datetime object."""
        try:
            # Handle common date strings
            date_str_lower = date_str.lower()
            if date_str_lower == "today":
                date = datetime.now().date()
            elif date_str_lower == "tomorrow":
                date = (datetime.now() + timedelta(days=1)).date()
            elif "next" in date_str_lower:
                # Simple handling for "next Monday", etc.
                days_ahead = 7  # Default to next week
                date = (datetime.now() + timedelta(days=days_ahead)).date()
            else:
                # Try to parse the date string
                from dateutil import parser
                date = parser.parse(date_str).date()
            
            # Parse time
            time_str_lower = time_str.lower().replace(" ", "")
            
            # Handle common time formats
            if time_str_lower == "noon":
                hour, minute = 12, 0
            elif time_str_lower == "midnight":
                hour, minute = 0, 0
            else:
                # Remove am/pm for parsing
                time_clean = time_str_lower.replace("am", "").replace("pm", "").strip()
                
                # Parse hour and minute
                if ":" in time_clean:
                    hour, minute = map(int, time_clean.split(":"))
                else:
                    hour = int(time_clean)
                    minute = 0
                
                # Adjust for PM
                if "pm" in time_str_lower and hour < 12:
                    hour += 12
                elif "am" in time_str_lower and hour == 12:
                    hour = 0
            
            # Combine date and time
            return datetime.combine(date, datetime.min.time().replace(hour=hour, minute=minute))
            
        except Exception as e:
            logger.error(f"Error parsing datetime: {e}")
            # Default to tomorrow at 9 AM
            tomorrow = datetime.now() + timedelta(days=1)
            return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
    
    def _get_recurrence_rule(self, frequency: str) -> List[str]:
        """Convert frequency description to Google Calendar recurrence rule."""
        frequency_lower = frequency.lower()
        
        if "daily" in frequency_lower or "every day" in frequency_lower:
            return ["RRULE:FREQ=DAILY"]
        elif "weekly" in frequency_lower or "once a week" in frequency_lower:
            return ["RRULE:FREQ=WEEKLY"]
        elif "twice" in frequency_lower and "day" in frequency_lower:
            # Twice a day - morning and evening
            return ["RRULE:FREQ=DAILY", "RRULE:FREQ=DAILY;BYHOUR=21"]
        elif "three times" in frequency_lower:
            # Three times a day
            return ["RRULE:FREQ=DAILY", "RRULE:FREQ=DAILY;BYHOUR=14", "RRULE:FREQ=DAILY;BYHOUR=21"]
        elif "every" in frequency_lower and "hours" in frequency_lower:
            # Extract hours if specified
            try:
                import re
                hours = re.search(r'(\d+)\s*hours?', frequency_lower)
                if hours:
                    interval = int(hours.group(1))
                    return [f"RRULE:FREQ=HOURLY;INTERVAL={interval}"]
            except:
                pass
        
        # Default to daily
        return ["RRULE:FREQ=DAILY"]