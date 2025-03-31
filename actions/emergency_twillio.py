import os
import logging
from twilio.rest import Client
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet

# Set up logging
logger = logging.getLogger(__name__)

# Initialize Twilio client
twilio_account_sid = os.getenv("TWILIO_ACCOUNT_SID")
twilio_auth_token = os.getenv("TWILIO_AUTH_TOKEN")
twilio_from_number = os.getenv("TWILIO_FROM_NUMBER")
emergency_contact = os.getenv("EMERGENCY_CONTACT_NUMBER")

if twilio_account_sid and twilio_auth_token and twilio_from_number:
    twilio_client = Client(twilio_account_sid, twilio_auth_token)
    logger.info("Twilio client initialized successfully")
else:
    logger.warning("Twilio credentials not fully configured. SMS functionality will be limited.")
    twilio_client = None

def send_emergency_sms(message):
    """Send an emergency SMS using Twilio"""
    if not twilio_client or not emergency_contact:
        logger.error("Cannot send emergency SMS: Twilio not configured properly")
        return False
    
    try:
        twilio_client.messages.create(
            body=message,
            from_=twilio_from_number,
            to=emergency_contact
        )
        logger.info(f"Emergency SMS sent to {emergency_contact}")
        return True
    except Exception as e:
        logger.error(f"Failed to send emergency SMS: {str(e)}")
        return False

class ActionEmergencyTwilio(Action):
    """Send emergency SMS using Twilio when triggered"""

    def name(self) -> Text:
        return "emergency_twillio"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        user_name = tracker.get_slot("name") or "User"
        user_location = tracker.get_slot("location") or "unknown location"
        
        # Create emergency message
        emergency_message = f"NOTFALL-ALARM: {user_name} hat über den Assistenten einen Hilferuf gesendet. "
        
        if user_location:
            emergency_message += f"Letzter bekannter Standort: {user_location}. "
        
        # Add the last message for context
        last_message = tracker.latest_message.get("text", "")
        if last_message:
            emergency_message += f"\nLetzte Nachricht: '{last_message}'"
        
        # Send the emergency SMS
        success = send_emergency_sms(emergency_message)
        
        # Return value to be used in the flow control
        result = "success" if success else "failed"
        logger.info(f"Setting return_value slot to: {result}")
        
        # Explicitly set the return_value slot
        return [SlotSet("return_value", result)]