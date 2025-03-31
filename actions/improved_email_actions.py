"""
Enhanced actions for email checking, reading, and navigation.
"""

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
import os
import logging
import json

from actions.improved_email_client import ImprovedEmailClient

# Set up logger
logger = logging.getLogger(__name__)

class ActionListEmails(Action):
    """Action to list all emails in a numbered format."""
    
    def name(self) -> Text:
        return "action_list_emails"
    
    def run(self, dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        List all unread emails in a numbered format.
        """
        try:
            # Initialize email client
            credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH")
            token_path = os.getenv("GMAIL_TOKEN_PATH")
            
            email_client = ImprovedEmailClient(
                credentials_path=credentials_path,
                token_path=token_path
            )
            
            # Get unread emails - increased max to 10
            unread_emails = email_client.get_unread_emails(max_results=10)
            
            if not unread_emails:
                dispatcher.utter_message(text="You don't have any new emails at the moment.")
                return [SlotSet("emails", None), SlotSet("email_count", 0)]
            
            # Store all emails in a slot as JSON
            emails_json = json.dumps(unread_emails)
            
            # Create a numbered list of emails - REMOVE THE QUESTION AT THE END
            email_list = "Here are your unread emails:\n\n"
            for i, email in enumerate(unread_emails, 1):
                email_list += f"{i}. From: {email['sender_name']} ({email['sender']})\n"
                email_list += f"   Subject: {email['subject']}\n"
                email_list += f"   Received: {email['date']}\n\n"
            
            # Remove the question line from here as it will be handled by utter_ask_selected_email
            
            dispatcher.utter_message(text=email_list)
            
            # Return events to set slots with all emails
            return [
                SlotSet("emails", emails_json),
                SlotSet("email_count", len(unread_emails)),
                SlotSet("current_email_index", 0) # Initialize index
            ]
            
        except Exception as e:
            logger.error(f"Error listing emails: {str(e)}")
            dispatcher.utter_message(
                text="I'm having trouble accessing your emails right now. Please check your internet connection and email authentication."
            )
            return []

class ValidateSelectedEmail(Action):
    def name(self) -> str:
        return "validate_selected_email"
        
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict) -> List[dict]:
        value = tracker.get_slot("selected_email")
        
        if value is None:
            return []
        
        # Accept both numeric and text values
        if isinstance(value, str):
            # If it's a digit, ensure it's valid
            if value.isdigit():
                return [SlotSet("selected_email", value)]
            # Otherwise, just return the text value
            return [SlotSet("selected_email", value)]
            
        return []

class ActionReadSelectedEmail(Action):
    """Action to read a specific email by number or description."""
    
    def name(self) -> Text:
        return "action_read_selected_email"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Read a specific email selected by the user.
        """
        try:
            # Get the selected email index or description
            selected = tracker.get_slot("selected_email")
            emails_json = tracker.get_slot("emails")
            
            if not emails_json:
                dispatcher.utter_message(text="I don't have any emails to show. Let's check your inbox first.")
                return []
            
            # Parse emails from JSON
            emails = json.loads(emails_json)
            
            # Determine which email to show
            index = 0
            
            # If selected is a number, use it as index
            if selected and selected.isdigit() and 1 <= int(selected) <= len(emails):
                index = int(selected) - 1
            elif selected:
                # Try to find by partial match on sender or subject
                selected = selected.lower()
                for i, email in enumerate(emails):
                    if (selected in email['sender'].lower() or 
                        selected in email['sender_name'].lower() or 
                        selected in email['subject'].lower()):
                        index = i
                        break
            
            # Get the email
            email = emails[index]
            
            # Format the email for display
            email_text = f"Email #{index+1}:\n"
            email_text += f"From: {email['sender_name']} ({email['sender']})\n"
            email_text += f"Subject: {email['subject']}\n"
            email_text += f"Received: {email['date']}\n\n"
            email_text += f"{email['body']}\n\n"
            
            # Display email
            dispatcher.utter_message(text=email_text)
                        
            # Set current email slots
            return [
                SlotSet("current_email_id", email["id"]),
                SlotSet("current_email_sender", f"{email['sender_name']} ({email['sender']})"),
                SlotSet("current_email_subject", email["subject"]),
                SlotSet("current_email_content", email["body"]),
                SlotSet("current_email_index", index)
            ]
            
        except Exception as e:
            logger.error(f"Error reading selected email: {str(e)}")
            dispatcher.utter_message(
                text="I encountered an error while reading your email. Please try again."
            )
            return []

class ActionNavigateEmails(Action):
    """Action to navigate to next or previous email with improved error handling."""
    
    def name(self) -> Text:
        return "action_navigate_emails"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Navigate to the next or previous email with proper error handling.
        """
        try:
            # Get navigation direction
            direction = tracker.get_slot("navigation_direction")
            current_index = tracker.get_slot("current_email_index")
            emails_json = tracker.get_slot("emails")
            
            if not emails_json or current_index is None:
                dispatcher.utter_message(text="I don't have email details to navigate. Let's check your inbox first.")
                return []
            
            # Parse emails from JSON
            emails = json.loads(emails_json)
            
            # Calculate new index
            new_index = current_index
            if direction == "next" and current_index < len(emails) - 1:
                new_index = current_index + 1
            elif direction == "previous" and current_index > 0:
                new_index = current_index - 1
            else:
                # Handle case when there are no more emails to navigate to
                if direction == "next":
                    dispatcher.utter_message(text="You've reached the end of your emails. There are no more emails to display.")
                elif direction == "previous":
                    dispatcher.utter_message(text="You're already at the first email. There are no previous emails to display.")
                else:
                    dispatcher.utter_message(text=f"I couldn't understand the navigation direction: {direction}.")
                
                # Return without attempting to navigate, but don't reset the current index
                return []
            
            # Get the email
            email = emails[new_index]
            
            # Format the email for display
            email_text = f"Email #{new_index+1}:\n"
            email_text += f"From: {email['sender_name']} ({email['sender']})\n"
            email_text += f"Subject: {email['subject']}\n"
            email_text += f"Received: {email['date']}\n\n"
            email_text += f"{email['body']}\n\n"
            
            # Display email
            dispatcher.utter_message(text=email_text)
            
            # Display action options (only show relevant navigation options)
            options = "What would you like to do with this email?\n"
            options += "1. Reply\n"
            options += "2. Mark as read\n"
            options += "3. Delete\n"
            options += "4. Apply label\n"
            
            if new_index < len(emails) - 1:
                options += "5. Next email\n"
                
            if new_index > 0:
                options += "6. Previous email\n"
                
            options += "7. Return to inbox"
            
            dispatcher.utter_message(text=options)
            
            # Set current email slots
            return [
                SlotSet("current_email_id", email["id"]),
                SlotSet("current_email_sender", f"{email['sender_name']} ({email['sender']})"),
                SlotSet("current_email_subject", email["subject"]),
                SlotSet("current_email_content", email["body"]),
                SlotSet("current_email_index", new_index)
            ]
            
        except Exception as e:
            logger.error(f"Error navigating emails: {str(e)}")
            dispatcher.utter_message(
                text="I encountered an error while navigating your emails. Please try again or check your inbox."
            )
            return []