"""
Actions for handling special email cases like no-reply addresses.
"""

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
import logging
import re

logger = logging.getLogger(__name__)

class ActionCheckForNoReply(Action):
    """Action to check if the current email is from a no-reply address."""
    
    def name(self) -> Text:
        return "action_check_for_noreply"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Check if the current email is from a no-reply address.
        """
        try:
            # Get the sender from slot
            sender = tracker.get_slot("current_email_sender")
            
            if not sender:
                # If no sender, assume not no-reply
                return [SlotSet("is_noreply_address", False)]
            
            # Check for common no-reply patterns in the sender address
            is_noreply = False
            noreply_patterns = [
                r'no[-\.]?reply',
                r'do[-\.]?not[-\.]?reply',
                r'no[-\.]?response',
                r'automated',
                r'noreply',
                r'donotreply'
            ]
            
            for pattern in noreply_patterns:
                if re.search(pattern, sender.lower()):
                    is_noreply = True
                    break
            
            # Set the slot
            return [SlotSet("is_noreply_address", is_noreply)]
            
        except Exception as e:
            logger.error(f"Error checking for no-reply: {str(e)}")
            # Default to False on error
            return [SlotSet("is_noreply_address", False)]