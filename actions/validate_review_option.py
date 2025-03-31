"""
Validator for review_option to handle various send commands.
"""
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet, FollowupAction
from rasa_sdk.executor import CollectingDispatcher
import logging
import re  # Make sure re is imported

logger = logging.getLogger(__name__)

class ValidateReviewOption(Action):
    """Validates the review_option slot to handle different send commands."""
    
    def name(self) -> str:
        return "validate_review_option"
        
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict) -> List[dict]:
        """
        Validate and normalize variations of review commands.
        """
        value = tracker.get_slot("review_option")
        user_message = tracker.latest_message.get("text", "").lower()
        
        logger.info(f"Validating review_option: {value}, user message: {user_message}")
        
        # If we already have a normalized value, keep it
        if value in ["send", "edit", "start_over", "cancel"]:
            return []
            
        # Check for send variations
        send_patterns = [
            r'send\b', r'send it\b', r'send as\b', r'looks good\b', 
            r'good\b', r'proceed\b', r'go ahead\b', r'yes send\b',
            r'approved\b', r'that\'s good\b', r'that looks\b'
        ]
        
        for pattern in send_patterns:
            if re.search(pattern, user_message):
                logger.info(f"Normalized '{user_message}' to 'send'")
                return [SlotSet("review_option", "send")]
                
        # Check for edit variations
        edit_patterns = [
            r'edit\b', r'change\b', r'modify\b', r'revise\b', 
            r'fix\b', r'correction\b', r'update\b'
        ]
        
        for pattern in edit_patterns:
            if re.search(pattern, user_message):
                logger.info(f"Normalized '{user_message}' to 'edit'")
                return [SlotSet("review_option", "edit")]
                
        # Check for start over variations
        start_over_patterns = [
            r'start over\b', r'redo\b', r'rewrite\b', r'scratch\b'
        ]
        
        for pattern in start_over_patterns:
            if re.search(pattern, user_message):
                logger.info(f"Normalized '{user_message}' to 'start_over'")
                return [SlotSet("review_option", "start_over")]
                
        # Check for cancel variations
        cancel_patterns = [
            r'cancel\b', r'discard\b', r'never mind\b', r'don\'t send\b'
        ]
        
        for pattern in cancel_patterns:
            if re.search(pattern, user_message):
                logger.info(f"Normalized '{user_message}' to 'cancel'")
                return [SlotSet("review_option", "cancel")]
                
        # If no pattern matches but we have some value, return it
        if value:
            return []
            
        # No match and no existing value
        return []