"""
Custom validation action for reply_type slot.
"""
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
import logging

logger = logging.getLogger(__name__)

class ValidateReplyType(Action):
    """Validates the reply_type slot value."""
    
    def name(self) -> Text:
        return "validate_reply_type"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Validate the reply_type slot value.
        Maps various inputs to the standardized values: user_content, professional, casual, custom
        """
        value = tracker.get_slot("reply_type")
        
        logger.info(f"Validating reply_type value: {value}")
        
        if value is None:
            return []
        
        # Normalize number inputs
        if value in ["1", "one", "first", "option 1", "first option"]:
            return [SlotSet("reply_type", "user_content")]
        
        if value in ["2", "two", "second", "option 2", "second option"]:
            return [SlotSet("reply_type", "professional")]
        
        if value in ["3", "three", "third", "option 3", "third option"]:
            return [SlotSet("reply_type", "casual")]
        
        if value in ["4", "four", "fourth", "option 4", "fourth option"]:
            return [SlotSet("reply_type", "custom")]
        
        # Normalize text inputs
        if any(kw in value.lower() for kw in ["own words", "my words", "write", "myself"]):
            return [SlotSet("reply_type", "user_content")]
        
        if any(kw in value.lower() for kw in ["professional", "formal", "business"]):
            return [SlotSet("reply_type", "professional")]
        
        if any(kw in value.lower() for kw in ["casual", "friendly", "informal"]):
            return [SlotSet("reply_type", "casual")]
        
        # For values not matching the above patterns, we'll just use the value as is
        # If the value doesn't match our standard types, we'll treat it as a custom style
        if value.lower() not in ["user_content", "professional", "casual", "custom"]:
            logger.info(f"Using custom style: {value}")
            return [SlotSet("reply_type", "custom"), SlotSet("custom_style", value)]
        
        return [SlotSet("reply_type", value)]
    
class ValidateReviewOption(Action):
    """Validates the review_option slot value."""
    
    def name(self) -> Text:
        return "validate_review_option"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Validate the review_option slot value.
        Maps various inputs to the standardized values: send, edit, start_over, cancel
        """
        value = tracker.get_slot("review_option")
        confirm_sending = tracker.get_slot("confirm_sending")
        
        logger.info(f"Validating review_option value: {value}")
        
        # If confirm_sending is already set, use it to set the review option
        if confirm_sending is True:
            return [SlotSet("review_option", "send")]
        elif confirm_sending is False:
            return [SlotSet("review_option", "cancel")]
        
        if value is None:
            return []
        
        # Normalize number inputs
        if value in ["1", "one", "first", "option 1", "first option", "send", "send it", "send as is"]:
            return [SlotSet("review_option", "send"), SlotSet("confirm_sending", True)]
        
        if value in ["2", "two", "second", "option 2", "second option", "edit", "edit it", "edit draft", "edit this"]:
            return [SlotSet("review_option", "edit"), SlotSet("confirm_sending", False)]
        
        if value in ["3", "three", "third", "option 3", "third option", "start over", "redo"]:
            return [SlotSet("review_option", "start_over"), SlotSet("confirm_sending", False)]
        
        if value in ["4", "four", "fourth", "option 4", "fourth option", "cancel", "forget it", "discard"]:
            return [SlotSet("review_option", "cancel"), SlotSet("confirm_sending", False)]
        
        # Handle more general phrases
        if any(kw in value.lower() for kw in ["send", "transmit", "deliver"]):
            return [SlotSet("review_option", "send"), SlotSet("confirm_sending", True)]
        
        if any(kw in value.lower() for kw in ["edit", "change", "modify", "revise"]):
            return [SlotSet("review_option", "edit"), SlotSet("confirm_sending", False)]
        
        if any(kw in value.lower() for kw in ["start over", "restart", "begin again", "new draft"]):
            return [SlotSet("review_option", "start_over"), SlotSet("confirm_sending", False)]
        
        if any(kw in value.lower() for kw in ["cancel", "discard", "abort", "don't send", "forget"]):
            return [SlotSet("review_option", "cancel"), SlotSet("confirm_sending", False)]
        
        # For unrecognized values, don't make assumptions
        logger.warning(f"Unrecognized review option: {value}")
        return []