"""
Custom validator for the selected_email slot.
"""

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
import logging
import json

logger = logging.getLogger(__name__)

class ValidateSelectedEmail(Action):
    """Validates the selected_email slot value."""
    
    def name(self) -> str:
        return "validate_selected_email"
        
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict) -> List[dict]:
        """
        Validate selected_email values, normalizing numeric inputs and checking against available emails.
        """
        value = tracker.get_slot("selected_email")
        emails_json = tracker.get_slot("emails")
        
        if value is None:
            return []
        
        logger.info(f"Validating selected_email: {value}")
        
        # Convert numeric words to numbers
        numeric_words = {
            "first": "1", "one": "1",
            "second": "2", "two": "2",
            "third": "3", "three": "3",
            "fourth": "4", "four": "4",
            "fifth": "5", "five": "5"
        }
        
        if value.lower() in numeric_words:
            value = numeric_words[value.lower()]
        
        # Check if we have emails to match against
        if emails_json:
            try:
                emails = json.loads(emails_json)
                
                # If it's a digit, ensure it's valid
                if value.isdigit():
                    email_index = int(value)
                    if 1 <= email_index <= len(emails):
                        return [SlotSet("selected_email", value)]
                    else:
                        dispatcher.utter_message(text=f"I don't see an email {value} in your inbox. Please choose a number between 1 and {len(emails)}.")
                        return [SlotSet("selected_email", None)]
                
                # Check if the value matches any part of an email (sender or subject)
                value_lower = value.lower()
                for i, email in enumerate(emails, 1):
                    sender_match = value_lower in email.get('sender_name', '').lower() or value_lower in email.get('sender', '').lower()
                    subject_match = value_lower in email.get('subject', '').lower()
                    
                    if sender_match or subject_match:
                        # Found a match, return the index as a string
                        return [SlotSet("selected_email", str(i))]
                
                # No match found
                dispatcher.utter_message(text=f"I couldn't find an email matching '{value}'. Please try again.")
                return [SlotSet("selected_email", None)]
                
            except (json.JSONDecodeError, TypeError) as e:
                logger.error(f"Error processing emails JSON: {e}")
        
        # If no emails or couldn't process, just return the value as is
        return [SlotSet("selected_email", value)]