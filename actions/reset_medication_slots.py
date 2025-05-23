"""
Action to reset medication reminder slots for setting up multiple reminders.
Save this as: actions/reset_medication_slots.py
"""
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

class ActionResetMedicationSlots(Action):
    """Reset all medication-related slots to allow setting up multiple reminders."""
    
    def name(self) -> Text:
        return "action_reset_medication_slots"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """Reset medication reminder slots."""
        return [
            SlotSet("medication_name", None),
            SlotSet("reminder_time", None),
            SlotSet("reminder_date", None),
            SlotSet("reminder_frequency", None),
            SlotSet("return_value", None),
            SlotSet("another_reminder", None),
            SlotSet("retry_reminder", None)
        ]