"""
New actions for OpenAI fallback, medication reminders, and help tracking.
Replace your existing actions/new_actions.py with this file.
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
    """Create a medication reminder in Google Calendar with improved error handling."""
    
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
            
            logger.info(f"Creating reminder for: {medication}, time: {time_str}, date: {date_str}, frequency: {frequency}")
            
            # Validate required slots
            if not medication:
                logger.error("Missing medication name")
                dispatcher.utter_message(text="I need to know which medication to remind you about.")
                return [SlotSet("return_value", "failed")]
            
            if not time_str:
                logger.error("Missing reminder time")
                dispatcher.utter_message(text="I need to know what time to remind you.")
                return [SlotSet("return_value", "failed")]
            
            # Set defaults for missing optional fields
            if not date_str:
                date_str = "today"
            if not frequency:
                frequency = "daily"
            
            # Initialize Google Calendar API
            service = self._get_calendar_service()
            if not service:
                logger.error("Failed to initialize Google Calendar service")
                dispatcher.utter_message(text="I couldn't connect to Google Calendar. Please check your credentials.")
                return [SlotSet("return_value", "failed")]
            
            # Parse date and time
            try:
                reminder_datetime = self._parse_datetime(date_str, time_str)
                logger.info(f"Parsed datetime: {reminder_datetime}")
            except Exception as e:
                logger.error(f"Error parsing datetime: {e}")
                dispatcher.utter_message(text="I couldn't understand the date or time format. Please try again with a clearer format.")
                return [SlotSet("return_value", "failed")]
            
            # Create the event with proper structure
            event = {
                'summary': f'💊 Take {medication}',
                'description': f'Reminder to take your {medication}',
                'start': {
                    'dateTime': reminder_datetime.isoformat(),
                    'timeZone': 'Europe/Copenhagen',
                },
                'end': {
                    'dateTime': (reminder_datetime + timedelta(minutes=15)).isoformat(),
                    'timeZone': 'Europe/Copenhagen',
                },
                'reminders': {
                    'useDefault': False,
                    'overrides': [
                        {'method': 'popup', 'minutes': 0},
                        {'method': 'notification', 'minutes': 0},
                    ],
                },
            }
            
            # Add recurrence if specified
            recurrence_rule = self._get_recurrence_rule(frequency)
            if recurrence_rule:
                event['recurrence'] = [recurrence_rule]
                logger.info(f"Added recurrence rule: {recurrence_rule}")
            
            # Insert the event
            created_event = service.events().insert(calendarId='primary', body=event).execute()
            logger.info(f'Event created successfully: {created_event.get("id")}')
            
            return [SlotSet("return_value", "success")]
            
        except HttpError as e:
            logger.error(f"Google Calendar API error: {e}")
            error_details = e.error_details if hasattr(e, 'error_details') else str(e)
            dispatcher.utter_message(text=f"Google Calendar error: {error_details}. Please check your event details.")
            return [SlotSet("return_value", "failed")]
            
        except Exception as e:
            logger.error(f"Unexpected error creating medication reminder: {e}")
            dispatcher.utter_message(text="An unexpected error occurred while setting up your reminder. Please try again.")
            return [SlotSet("return_value", "failed")]
    
    def _get_calendar_service(self):
        """Initialize Google Calendar service with improved error handling."""
        SCOPES = ['https://www.googleapis.com/auth/calendar']
        
        try:
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
            
            # Ensure credentials directory exists
            os.makedirs(os.path.dirname(token_path), exist_ok=True)
            
            # Load existing token
            if os.path.exists(token_path):
                try:
                    with open(token_path, 'r') as token:
                        creds = Credentials.from_authorized_user_info(
                            json.load(token), SCOPES
                        )
                        logger.info("Loaded existing Google Calendar credentials")
                except Exception as e:
                    logger.error(f"Error loading existing token: {e}")
            
            # Refresh or get new credentials
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        logger.info("Refreshed Google Calendar credentials")
                    except Exception as e:
                        logger.error(f"Error refreshing token: {e}")
                        creds = None
                
                if not creds:
                    if not os.path.exists(credentials_path):
                        logger.error(f"Google Calendar credentials file not found at {credentials_path}")
                        return None
                    
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            credentials_path, SCOPES)
                        creds = flow.run_local_server(port=0)
                        
                        # Save the credentials
                        with open(token_path, 'w') as token:
                            json.dump(json.loads(creds.to_json()), token)
                        logger.info("Created new Google Calendar credentials")
                    except Exception as e:
                        logger.error(f"Error during OAuth flow: {e}")
                        return None
            
            # Build and return the service
            service = build('calendar', 'v3', credentials=creds)
            logger.info("Successfully built Google Calendar service")
            return service
            
        except Exception as e:
            logger.error(f"Failed to build Calendar service: {e}")
            return None
    
    def _parse_datetime(self, date_str: str, time_str: str) -> datetime:
        """Parse date and time strings into datetime object with better error handling."""
        try:
            # Clean up input strings
            date_str = date_str.strip().lower()
            time_str = time_str.strip().lower()
            
            logger.info(f"Parsing date: '{date_str}', time: '{time_str}'")
            
            # Handle common date strings
            today = datetime.now().date()
            if date_str in ["today", "heute"]:
                date = today
            elif date_str in ["tomorrow", "morgen"]:
                date = today + timedelta(days=1)
            elif "next" in date_str or "nächste" in date_str:
                # Simple handling for "next Monday", etc. - default to 7 days ahead
                date = today + timedelta(days=7)
            else:
                try:
                    # Try to parse various date formats
                    from dateutil import parser
                    parsed_date = parser.parse(date_str, default=datetime.now())
                    date = parsed_date.date()
                except:
                    # If all parsing fails, default to today
                    logger.warning(f"Could not parse date '{date_str}', defaulting to today")
                    date = today
            
            # Parse time with better handling
            hour, minute = self._parse_time(time_str)
            
            # Combine date and time
            result = datetime.combine(date, datetime.min.time().replace(hour=hour, minute=minute))
            logger.info(f"Successfully parsed datetime: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error parsing datetime: {e}")
            # Default to tomorrow at 9 AM if parsing fails
            tomorrow = datetime.now() + timedelta(days=1)
            return tomorrow.replace(hour=9, minute=0, second=0, microsecond=0)
    
    def _parse_time(self, time_str: str) -> tuple:
        """Parse time string and return (hour, minute) tuple."""
        try:
            time_str_clean = time_str.replace(" ", "").lower()
            
            # Handle special cases
            if time_str_clean in ["noon", "mittag"]:
                return (12, 0)
            elif time_str_clean in ["midnight", "mitternacht"]:
                return (0, 0)
            
            # Extract AM/PM indicator
            is_pm = "pm" in time_str_clean or "p.m." in time_str_clean
            is_am = "am" in time_str_clean or "a.m." in time_str_clean
            
            # Remove am/pm indicators
            time_clean = time_str_clean.replace("pm", "").replace("am", "").replace("p.m.", "").replace("a.m.", "").strip()
            
            # Parse hour and minute
            if ":" in time_clean:
                parts = time_clean.split(":")
                hour = int(parts[0])
                minute = int(parts[1]) if len(parts) > 1 else 0
            else:
                hour = int(time_clean)
                minute = 0
            
            # Adjust for AM/PM
            if is_pm and hour < 12:
                hour += 12
            elif is_am and hour == 12:
                hour = 0
            
            # Handle 24-hour format edge cases
            if hour >= 24:
                hour = hour % 24
            
            return (hour, minute)
            
        except Exception as e:
            logger.error(f"Error parsing time '{time_str}': {e}")
            # Default to 9 AM if parsing fails
            return (9, 0)
    
    def _get_recurrence_rule(self, frequency: str) -> str:
        """Convert frequency description to Google Calendar recurrence rule."""
        try:
            frequency_lower = frequency.lower().strip()
            logger.info(f"Processing frequency: '{frequency_lower}'")
            
            if any(word in frequency_lower for word in ["daily", "every day", "täglich"]):
                return "RRULE:FREQ=DAILY"
            elif any(word in frequency_lower for word in ["weekly", "once a week", "wöchentlich"]):
                return "RRULE:FREQ=WEEKLY"
            elif "twice" in frequency_lower and "day" in frequency_lower:
                return "RRULE:FREQ=DAILY;INTERVAL=1;BYHOUR=9,21"  # 9 AM and 9 PM
            elif "three times" in frequency_lower and "day" in frequency_lower:
                return "RRULE:FREQ=DAILY;INTERVAL=1;BYHOUR=8,14,20"  # 8 AM, 2 PM, 8 PM
            elif "every" in frequency_lower and "hour" in frequency_lower:
                # Extract hours if specified
                try:
                    import re
                    hours_match = re.search(r'(\d+)\s*hour', frequency_lower)
                    if hours_match:
                        interval = int(hours_match.group(1))
                        return f"RRULE:FREQ=HOURLY;INTERVAL={interval}"
                except:
                    pass
            
            # Default to daily if no specific pattern matches
            logger.info("No specific frequency pattern matched, defaulting to daily")
            return "RRULE:FREQ=DAILY"
            
        except Exception as e:
            logger.error(f"Error processing frequency '{frequency}': {e}")
            return "RRULE:FREQ=DAILY"