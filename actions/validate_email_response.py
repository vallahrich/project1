"""
Validator for the email_response slot to handle edited drafts.
"""

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet, FollowupAction
from rasa_sdk.executor import CollectingDispatcher
import logging

logger = logging.getLogger(__name__)

class ValidateEmailResponse(Action):
    """Validates the email_response slot and handles draft edits."""
    
    def name(self) -> str:
        return "validate_email_response"
        
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict) -> List[dict]:
        """
        Validate and process edits to email drafts.
        """
        value = tracker.get_slot("email_response")
        user_input = tracker.get_slot("user_input")
        
        # If we're in the edit phase and have user input, use it to update email_response
        if tracker.get_slot("reply_stage") == "review" and user_input:
            logger.info(f"Updating email response with user edits: {user_input}")
            
            # Format the user's input into a proper email
            # Get sender for proper greeting
            sender = tracker.get_slot("current_email_sender")
            recipient_name = "there"
            if sender and "(" in sender:
                full_name = sender.split("(")[0].strip()
                recipient_name = full_name.split()[0] if full_name else "there"
            
            # Create a new formatted email with the user's content
            updated_email = f"Subject: Re: {tracker.get_slot('current_email_subject')}\n\n"
            updated_email += f"Dear {recipient_name},\n\n"
            updated_email += f"{user_input}\n\n"
            updated_email += "Best regards,\nVincent Wallerich"
            
            # Clear the user_input slot to avoid confusion in future turns
            return [
                SlotSet("email_response", updated_email),
                SlotSet("user_input", None)
            ]
            
        return []