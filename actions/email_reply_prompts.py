"""
Actions for managing different reply prompts based on the reply type.
"""
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import FollowupAction, SlotSet 
from rasa_sdk.executor import CollectingDispatcher
import logging

logger = logging.getLogger(__name__)

class ActionSelectInputPrompt(Action):
    """Selects the appropriate input prompt based on reply type."""
    
    def name(self) -> Text:
        return "action_select_input_prompt"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Select and dispatch the appropriate utterance based on reply_type.
        """
        try:
            reply_type = tracker.get_slot("reply_type")
            custom_style = tracker.get_slot("custom_style")
            
            logger.info(f"Selecting input prompt for reply_type: {reply_type}")
            
            if reply_type == "user_content":
                return [FollowupAction("utter_ask_user_content_input")]
            elif reply_type == "professional":
                return [FollowupAction("utter_ask_professional_input")]
            elif reply_type == "casual":
                return [FollowupAction("utter_ask_casual_input")]
            elif reply_type == "custom" and custom_style:
                # If custom style is set, we need to fill the template variable
                dispatcher.utter_message(template="utter_ask_custom_input", 
                                        custom_style=custom_style)
                return []
            else:
                return [FollowupAction("utter_ask_default_input")]
                
        except Exception as e:
            logger.error(f"Error selecting input prompt: {str(e)}")
            # Fallback to default prompt
            return [FollowupAction("utter_ask_default_input")]

class ActionSetUserInput(Action):
    """Action to set user_input slot from user message."""
    
    def name(self) -> Text:
        return "action_set_user_input"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Extract the user's message and set it as user_input.
        """
        user_message = tracker.latest_message.get("text", "")
        logger.info(f"Setting user_input to: {user_message}")
        
        return [SlotSet("user_input", user_message)]