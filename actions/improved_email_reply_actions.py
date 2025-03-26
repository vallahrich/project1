"""
Enhanced actions for drafting and sending email replies.
"""

from typing import Any, Text, Dict, List
import os
import re
import requests
import json
import logging

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from actions.improved_email_client import ImprovedEmailClient

# Set up logger
logger = logging.getLogger(__name__)

class ActionInitiateReply(Action):
    """Action to initiate the email reply process with options."""
    
    def name(self) -> Text:
        return "action_initiate_reply"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Offer reply options to the user.
        """
        try:
            # Get email details from slots
            sender = tracker.get_slot("current_email_sender")
            subject = tracker.get_slot("current_email_subject")
            
            if not sender or not subject:
                dispatcher.utter_message(
                    text="I don't have an email selected to reply to. Let's check your inbox first."
                )
                return []
            
            # Extract sender name for personalization
            sender_name = sender.split('(')[0].strip() if '(' in sender else sender
            
            # Check if this is a no-reply address
            is_no_reply = any(term in sender.lower() for term in ["no-reply", "noreply", "do-not-reply", "donotreply"])
            
            if is_no_reply:
                warning = "⚠️ This appears to be a no-reply email address which typically doesn't accept responses.\n\n"
                dispatcher.utter_message(text=warning)
            
            # Offer different reply options
            message = f"I'll help you draft a reply to {sender_name} about \"{subject}\".\n\n"
            message += "How would you like to respond? You can:\n"
            message += "1. Tell me what to say in your own words\n"
            message += "2. Ask me to draft a professional reply\n"
            message += "3. Ask me to draft a casual reply\n"
            message += "4. Create a specific type of response (e.g., \"Draft a concerned reply\")"
            
            dispatcher.utter_message(text=message)
            
            return [SlotSet("reply_stage", "initiate")]
            
        except Exception as e:
            logger.error(f"Error initiating reply: {str(e)}")
            dispatcher.utter_message(
                text="I encountered an error while setting up your reply. Please try again later."
            )
            return []

class ActionGenerateReplyDraft(Action):
    """Action to generate different types of email reply drafts."""
    
    def name(self) -> Text:
        return "action_generate_reply_draft"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Generate a reply draft based on user's choice.
        """
        try:
            # Get the user's choice and input
            reply_type = tracker.get_slot("reply_type")
            user_input = tracker.get_slot("user_input")
            
            # Get email details from slots
            sender = tracker.get_slot("current_email_sender")
            subject = tracker.get_slot("current_email_subject")
            original_content = tracker.get_slot("current_email_content")
            email_id = tracker.get_slot("current_email_id")
            
            if not sender or not subject or not original_content:
                dispatcher.utter_message(
                    text="I don't have the original email details. Let's check your inbox first."
                )
                return []
            
            # Generate the appropriate reply based on the type
            if reply_type == "user_content" and user_input:
                draft = self.generate_reply_from_user_content(
                    user_input, sender, subject, original_content
                )
            elif reply_type == "professional":
                draft = self.generate_professional_reply(
                    sender, subject, original_content
                )
            elif reply_type == "casual":
                draft = self.generate_casual_reply(
                    sender, subject, original_content
                )
            elif reply_type == "custom" and user_input:
                draft = self.generate_custom_reply(
                    user_input, sender, subject, original_content
                )
            else:
                dispatcher.utter_message(
                    text="I need more information about what kind of reply you'd like to create. Could you please specify?"
                )
                return []
            
            # Display the draft
            message = "Here's the draft I've created:\n\n"
            message += "-----\n"
            message += f"To: {sender}\n"
            message += f"Subject: Re: {subject}\n\n"
            message += draft
            message += "\n-----\n\n"
            
            message += "Would you like to:\n"
            message += "1. Send as is\n"
            message += "2. Edit this draft\n"
            message += "3. Start over\n"
            message += "4. Save as draft"
            
            dispatcher.utter_message(text=message)
            
            # Update the email_response slot with the draft
            return [
                SlotSet("email_response", draft),
                SlotSet("reply_stage", "review")
            ]
            
        except Exception as e:
            logger.error(f"Error generating reply draft: {str(e)}")
            dispatcher.utter_message(
                text="I encountered an error while drafting your reply. Please try again later."
            )
            return []
    
    def generate_reply_from_user_content(self, content: str, sender: str, subject: str, original_content: str) -> str:
        """Generate a reply based on user's exact content with professional formatting."""
        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not found")
            return self._fallback_email_generation(content, sender)
        
        # Extract recipient name from sender
        recipient_name = "there"
        if "(" in sender and ")" in sender:
            full_name = sender.split("(")[0].strip()
            recipient_name = full_name.split()[0] if full_name else "there"
        
        # Prepare the prompt
        prompt = f"""
        Format the user's content into a professional email reply:
        
        Original email subject: {subject}
        Original email sender: {sender}
        
        User's content: {content}
        
        Create a well-formatted email that uses the user's content verbatim.
        Add an appropriate greeting and professional sign-off.
        Do not add any new content or change the user's message.
        """
        
        try:
            # Call OpenAI API
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-2024-11-20",
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant that formats emails."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.5
                },
                timeout=10
            )
            
            # Parse response
            response_data = response.json()
            email_text = response_data["choices"][0]["message"]["content"].strip()
            
            return email_text
            
        except Exception as e:
            logger.error(f"Error generating email with LLM: {e}")
            return self._fallback_email_generation(content, sender)
    
    def generate_professional_reply(self, sender: str, subject: str, original_content: str) -> str:
        """Generate a professional reply based on the original email content."""
        # Implementation similar to generate_reply_from_user_content but with different prompt
        # [Implementation omitted for brevity]
        pass
    
    def generate_casual_reply(self, sender: str, subject: str, original_content: str) -> str:
        """Generate a casual, friendly reply based on the original email content."""
        # Implementation similar to generate_reply_from_user_content but with different prompt
        # [Implementation omitted for brevity]
        pass
    
    def generate_custom_reply(self, style: str, sender: str, subject: str, original_content: str) -> str:
        """Generate a reply in a custom style specified by the user."""
        # Implementation similar to generate_reply_from_user_content but with different prompt
        # [Implementation omitted for brevity]
        pass
    
    def _fallback_email_generation(self, content: str, sender: str) -> str:
        """Fallback method for email generation without LLM."""
        # Extract recipient name from sender
        recipient_name = "there"
        if "(" in sender and ")" in sender:
            full_name = sender.split("(")[0].strip()
            recipient_name = full_name.split()[0] if full_name else "there"
        
        # Basic template
        greeting = f"Hello {recipient_name},"
        signature = "\n\nBest regards,\n[Your Name]"
        
        # Simple formatting as fallback
        formatted_content = f"{greeting}\n\n{content}\n{signature}"
        return formatted_content