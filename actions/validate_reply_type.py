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