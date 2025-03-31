# actions/reset_slots.py (already exists)
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

class ActionResetEmailSlots(Action):
    def name(self) -> Text:
        return "reset_email_slots"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        return [
            SlotSet("current_email_id", None),
            SlotSet("current_email_sender", None), 
            SlotSet("current_email_subject", None),
            SlotSet("current_email_content", None),
            SlotSet("current_email_index", None),
            SlotSet("selected_email", None),
            SlotSet("reply_stage", None),
            SlotSet("email_action", None),
            SlotSet("email_response", None),
            SlotSet("review_option", None),
            SlotSet("user_input", None),
            SlotSet("confirm_edited_draft", None)
        ]