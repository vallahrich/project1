"""
Enhanced actions for email checking, reading, and navigation - FIXED VERSION.
"""

from typing import Any, Text, Dict, List
from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher
import os
import logging
import json
import re

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
            
            # Create a numbered list of emails
            email_list = "Here are your unread emails:\n\n"
            for i, email in enumerate(unread_emails, 1):
                email_list += f"{i}. From: {email['sender_name']} ({email['sender']})\n"
                email_list += f"   Subject: {email['subject']}\n"
                email_list += f"   Received: {email['date']}\n\n"
            
            dispatcher.utter_message(text=email_list)
            
            # Return events to set slots with all emails
            return [
                SlotSet("emails", emails_json),
                SlotSet("email_count", len(unread_emails)),
                SlotSet("current_email_index", 0)
            ]
            
        except Exception as e:
            logger.error(f"Error listing emails: {str(e)}")
            dispatcher.utter_message(
                text="I'm having trouble accessing your emails right now. Please check your internet connection and email authentication."
            )
            return []

class ValidateSelectedEmail(Action):
    """FIXED validator for selected_email slot."""
    
    def name(self) -> str:
        return "validate_selected_email"
        
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: dict) -> List[dict]:
        """
        IMPROVED validation for selected_email values with better pattern matching.
        """
        value = tracker.get_slot("selected_email")
        emails_json = tracker.get_slot("emails")
        
        if value is None:
            return []
        
        logger.info(f"Validating selected_email: '{value}'")
        
        # Check if we have emails to match against
        if not emails_json:
            dispatcher.utter_message(text="I don't have any emails loaded. Let me check your inbox first.")
            return [SlotSet("selected_email", None)]
        
        try:
            emails = json.loads(emails_json)
            logger.info(f"Found {len(emails)} emails to match against")
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"Error parsing emails JSON: {e}")
            return [SlotSet("selected_email", None)]
        
        # Convert numeric words to numbers
        numeric_words = {
            "first": "1", "one": "1", "1st": "1",
            "second": "2", "two": "2", "2nd": "2", 
            "third": "3", "three": "3", "3rd": "3",
            "fourth": "4", "four": "4", "4th": "4",
            "fifth": "5", "five": "5", "5th": "5"
        }
        
        value_lower = value.lower().strip()
        
        # Check for numeric word conversion
        for word, num in numeric_words.items():
            if word in value_lower:
                value_lower = value_lower.replace(word, num)
                break
        
        # Extract number from patterns like "number 2", "email 2", "2 from vincent"
        number_match = re.search(r'\b(\d+)\b', value_lower)
        if number_match:
            email_number = int(number_match.group(1))
            if 1 <= email_number <= len(emails):
                logger.info(f"Successfully matched email number: {email_number}")
                return [SlotSet("selected_email", str(email_number))]
            else:
                dispatcher.utter_message(text=f"I only have {len(emails)} emails. Please choose a number between 1 and {len(emails)}.")
                return [SlotSet("selected_email", None)]
        
        # If it's just a digit, validate it
        if value_lower.isdigit():
            email_index = int(value_lower)
            if 1 <= email_index <= len(emails):
                logger.info(f"Successfully validated direct number: {email_index}")
                return [SlotSet("selected_email", value_lower)]
            else:
                dispatcher.utter_message(text=f"I only have {len(emails)} emails. Please choose a number between 1 and {len(emails)}.")
                return [SlotSet("selected_email", None)]
        
        # Try to match by sender name or subject
        for i, email in enumerate(emails, 1):
            sender_name = email.get('sender_name', '').lower()
            sender_email = email.get('sender', '').lower()
            subject = email.get('subject', '').lower()
            
            # Check if any part of the value matches sender or subject
            value_parts = value_lower.split()
            for part in value_parts:
                if len(part) > 2:  # Only check meaningful parts
                    if (part in sender_name or part in sender_email or part in subject):
                        logger.info(f"Matched email {i} by keyword '{part}'")
                        return [SlotSet("selected_email", str(i))]
        
        # If no match found, provide helpful message
        dispatcher.utter_message(text=f"I couldn't find an email matching '{value}'. Please try:\n- A number (1, 2, 3...)\n- The sender's name\n- Part of the subject line")
        return [SlotSet("selected_email", None)]

class ActionReadSelectedEmail(Action):
    """ENHANCED action to read a specific email with full details."""
    
    def name(self) -> Text:
        return "action_read_selected_email"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Read and display a specific email with full details and better formatting.
        """
        try:
            # Get the selected email index
            selected = tracker.get_slot("selected_email")
            emails_json = tracker.get_slot("emails")
            
            if not emails_json:
                dispatcher.utter_message(text="I don't have any emails to show. Let me check your inbox first.")
                return []
            
            if not selected:
                dispatcher.utter_message(text="Please tell me which email you'd like to read.")
                return []
            
            # Parse emails from JSON
            emails = json.loads(emails_json)
            
            # Get the email index (convert to 0-based)
            if selected.isdigit():
                email_index = int(selected) - 1
            else:
                # This shouldn't happen with proper validation, but handle it
                email_index = 0
            
            if email_index < 0 or email_index >= len(emails):
                dispatcher.utter_message(text=f"Email number {selected} is not available. Please choose between 1 and {len(emails)}.")
                return []
            
            # Get the email
            email = emails[email_index]
            
            # Format the email for detailed display
            email_text = f"**EMAIL #{email_index + 1}**\n"
            email_text += f"═══════════════════════════════════\n\n"
            
            # Header information
            email_text += f"**From:** {email['sender_name']}\n"
            email_text += f"**Email:** {email['sender']}\n"
            email_text += f"**Subject:** {email['subject']}\n"
            email_text += f"**Date:** {email['date']}\n"
            email_text += f"**Status:** {'Unread' if not email.get('read', False) else 'Read'}\n\n"
            
            # Email content
            email_text += f"**MESSAGE:**\n"
            email_text += f"─────────────────────────────────────\n"
            
            # Get email body and clean it up
            body = email.get('body', email.get('snippet', 'No content available'))
            if body:
                # Clean up common email formatting issues
                cleaned_body = self._clean_email_body(body)
                email_text += f"{cleaned_body}\n"
            else:
                email_text += "No message content available.\n"
            
            email_text += f"─────────────────────────────────────\n\n"
            
            # Add options
            email_text += "**What would you like to do with this email?**\n"
            email_text += "• Say 'reply' to respond\n"
            email_text += "• Say 'mark as read' to mark it as read\n"
            email_text += "• Say 'delete' to delete it\n"
            email_text += "• Say 'label' to add a label\n"
            email_text += "• Say 'next' or 'previous' to navigate\n"
            email_text += "• Say 'back to inbox' to return to the email list"
            
            # Display the formatted email
            dispatcher.utter_message(text=email_text)
            
            # Set current email slots for further actions
            return [
                SlotSet("current_email_id", email["id"]),
                SlotSet("current_email_sender", f"{email['sender_name']} ({email['sender']})"),
                SlotSet("current_email_subject", email["subject"]),
                SlotSet("current_email_content", email.get('body', email.get('snippet', ''))),
                SlotSet("current_email_index", email_index)
            ]
            
        except Exception as e:
            logger.error(f"Error reading selected email: {str(e)}")
            dispatcher.utter_message(
                text="I encountered an error while reading your email. Please try again or select a different email."
            )
            return []
    
    def _clean_email_body(self, body: str) -> str:
        """Clean up email body for better display."""
        if not body:
            return "No content available"
        
        # Remove excessive line breaks
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', body)
        
        # Remove unicode characters that don't display well
        cleaned = re.sub(r'[\u034f\u200c]+', '', cleaned)
        
        # Clean up excessive whitespace
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        
        # Limit length for readability (keep first 1000 characters)
        if len(cleaned) > 1000:
            cleaned = cleaned[:1000] + "\n\n[Message truncated - full content available in Gmail]"
        
        return cleaned.strip()

class ActionNavigateEmails(Action):
    """IMPROVED action to navigate to next or previous email."""
    
    def name(self) -> Text:
        return "action_navigate_emails"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Navigate to the next or previous email with better error handling.
        """
        try:
            # Get navigation direction
            direction = tracker.get_slot("navigation_direction")
            current_index = tracker.get_slot("current_email_index")
            emails_json = tracker.get_slot("emails")
            
            if not emails_json or current_index is None:
                dispatcher.utter_message(text="I don't have email details to navigate. Let me check your inbox first.")
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
                # Handle edge cases
                if direction == "next":
                    dispatcher.utter_message(text="You're already at the last email. There are no more emails to display.")
                elif direction == "previous":
                    dispatcher.utter_message(text="You're already at the first email. There are no previous emails to display.")
                else:
                    dispatcher.utter_message(text=f"I didn't understand the navigation direction: {direction}. Please say 'next' or 'previous'.")
                
                return []
            
            # Get the email and display it using the same logic as ActionReadSelectedEmail
            email = emails[new_index]
            
            # Create the same detailed format
            email_text = f"📧 **EMAIL #{new_index + 1}**\n"
            email_text += f"═══════════════════════════════════\n\n"
            
            email_text += f"**From:** {email['sender_name']}\n"
            email_text += f"**Email:** {email['sender']}\n"
            email_text += f"**Subject:** {email['subject']}\n"
            email_text += f"**Date:** {email['date']}\n\n"
            
            email_text += f"**MESSAGE:**\n"
            email_text += f"─────────────────────────────────────\n"
            
            body = email.get('body', email.get('snippet', 'No content available'))
            if body:
                cleaned_body = self._clean_email_body(body)
                email_text += f"{cleaned_body}\n"
            else:
                email_text += "No message content available.\n"
            
            email_text += f"─────────────────────────────────────\n\n"
            
            # Add navigation info
            email_text += f"**Email {new_index + 1} of {len(emails)}**\n\n"
            
            # Add action options
            email_text += "**What would you like to do?**\n"
            email_text += "• Reply • Mark as read • Delete • Label\n"
            if new_index < len(emails) - 1:
                email_text += "• Next email\n"
            if new_index > 0:
                email_text += "• Previous email\n"
            email_text += "• Back to inbox"
            
            dispatcher.utter_message(text=email_text)
            
            # Set current email slots
            return [
                SlotSet("current_email_id", email["id"]),
                SlotSet("current_email_sender", f"{email['sender_name']} ({email['sender']})"),
                SlotSet("current_email_subject", email["subject"]),
                SlotSet("current_email_content", email.get('body', email.get('snippet', ''))),
                SlotSet("current_email_index", new_index)
            ]
            
        except Exception as e:
            logger.error(f"Error navigating emails: {str(e)}")
            dispatcher.utter_message(
                text="I encountered an error while navigating your emails. Please try again or check your inbox."
            )
            return []
    
    def _clean_email_body(self, body: str) -> str:
        """Clean up email body for better display - same as ActionReadSelectedEmail."""
        if not body:
            return "No content available"
        
        cleaned = re.sub(r'\n\s*\n\s*\n', '\n\n', body)
        cleaned = re.sub(r'[\u034f\u200c]+', '', cleaned)
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        
        if len(cleaned) > 1000:
            cleaned = cleaned[:1000] + "\n\n[Message truncated - full content available in Gmail]"
        
        return cleaned.strip()