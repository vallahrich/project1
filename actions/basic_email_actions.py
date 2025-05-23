"""
Basic email operations for email management.
"""
from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
import logging

from actions.improved_email_client import ImprovedEmailClient

logger = logging.getLogger(__name__)

class ActionDeleteEmail(Action):
    """Action to delete the current email."""
    
    def name(self) -> Text:
        return "action_delete_email"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Delete the current email.
        """
        try:
            # Get email ID from slot
            email_id = tracker.get_slot("current_email_id")
            if not email_id:
                dispatcher.utter_message(text="Ich habe keine E-Mail ausgewählt, die gelöscht werden soll.")
                return []
            
            # Initialize the email client
            client = ImprovedEmailClient()
            
            # Try to delete the email
            success = client.trash_email(email_id)
            
            if success:
                dispatcher.utter_message(text="Die E-Mail wurde in den Papierkorb verschoben.")
                # Clear current email slots since it's deleted
                return [
                    SlotSet("current_email_id", None),
                    SlotSet("current_email_sender", None),
                    SlotSet("current_email_subject", None),
                    SlotSet("current_email_content", None)
                ]
            else:
                dispatcher.utter_message(text="Ich konnte die E-Mail nicht löschen. Bitte versuche es erneut.")
                return []
            
        except Exception as e:
            logger.error(f"Error deleting email: {e}")
            dispatcher.utter_message(text="Ich bin auf einen Fehler gestoßen, während ich versuchte, die E-Mail zu löschen.")
            return []

class ActionMarkAsRead(Action):
    """Action to mark the current email as read."""
    
    def name(self) -> Text:
        return "action_mark_as_read"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Mark the current email as read.
        """
        try:
            # Get email ID from slot
            email_id = tracker.get_slot("current_email_id")
            if not email_id:
                dispatcher.utter_message(text="Ich habe keine E-Mail ausgewählt, die als gelesen markiert werden soll.")
                return []
            
            # Initialize the email client
            client = ImprovedEmailClient()
            
            # Try to mark the email as read
            success = client.mark_as_read(email_id)
            
            if success:
                dispatcher.utter_message(text="Die E-Mail wurde als gelesen markiert.")
                return []
            else:
                dispatcher.utter_message(text="Ich konnte die E-Mail nicht als gelesen markieren. Bitte versuche es erneut.")
                return []
            
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
            dispatcher.utter_message(text="Ich bin auf einen Fehler gestoßen, während ich versuchte, die E-Mail als gelesen zu markieren.")
            return []