"""
Actions for checking and reading emails.
"""


from typing import Any, Text, Dict, List
from rasa_sdk import Action, RasaProTracker, RasaProSlot
from rasa_sdk.executor import CollectingDispatcher
import os
import logging

from actions.email_client import EmailClient

# Set up logger
logger = logging.getLogger(__name__)

class ActionCheckNewMail(Action):
    """Action to check for new emails."""
    
    def name(self) -> Text:
        return "action_check_new_mail"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: RasaProTracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Check for new emails and report the most recent one.
        
        Args:
            dispatcher: Dispatcher to send messages to the user
            tracker: Tracker to get conversation state
            domain: Domain with parameters
            
        Returns:
            List of events to update the conversation state
        """
        try:
            # Initialize email client with credentials from environment
            credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH")
            token_path = os.getenv("GMAIL_TOKEN_PATH")
            
            email_client = EmailClient(
                credentials_path=credentials_path,
                token_path=token_path
            )
            
            # Get unread emails - default max_results is 5
            unread_emails = email_client.get_unread_emails()
            
            if not unread_emails:
                dispatcher.utter_message(text="You don't have any new emails at the moment.")
                return []
            
            # Store the most recent unread email in slots
            email = unread_emails[0]
            
            # Create a more conversational message
            if len(unread_emails) == 1:
                message = f"You have one new email from {email['sender_name']} with the subject: \"{email['subject']}\""
            else:
                message = f"You have {len(unread_emails)} new emails. The most recent one is from {email['sender_name']} with the subject: \"{email['subject']}\""
            
            dispatcher.utter_message(text=message)
            
            # Return events to set slots with email details
            return [
                RasaProSlot("current_email_id", email["id"]),
                RasaProSlot("current_email_sender", f"{email['sender_name']} ({email['sender']})"),
                RasaProSlot("current_email_subject", email["subject"]),
                RasaProSlot("current_email_content", email["body"])
            ]
            
        except Exception as e:
            logger.error(f"Error checking emails: {str(e)}")
            dispatcher.utter_message(
                text="I'm having trouble accessing your emails right now. Please check your internet connection and email authentication."
            )
            return []


class ActionReadMail(Action):
    """Action to read the content of the current email."""
    
    def name(self) -> Text:
        return "action_read_mail"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: RasaProTracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Read the content of the current email.
        
        Args:
            dispatcher: Dispatcher to send messages to the user
            tracker: Tracker to get conversation state
            domain: Domain with parameters
            
        Returns:
            Empty list as this action doesn't update the conversation state
        """
        # Get email details from slots
        sender = tracker.get_slot("current_email_sender")
        subject = tracker.get_slot("current_email_subject")
        content = tracker.get_slot("current_email_content")
        
        if not sender or not subject or not content:
            dispatcher.utter_message(text="I don't have any email details to read.")
            return []
        
        # Prepare the email content for reading
        # Format the email in a readable way
        email_text = (
            f"From: {sender}\n"
            f"Subject: {subject}\n\n"
            f"{content}"
        )
        
        # Send the formatted email text to the user
        dispatcher.utter_message(text=email_text)
        
        # Offer follow-up actions
        dispatcher.utter_message(
            text="Would you like to reply to this email, label it, or check for other emails?"
        )
        
        return []