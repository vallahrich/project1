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
            
            # No need to display the draft here since we're now using utter_ask_draft_options
            # which will be rendered with the draft content
            
            # Update the email_response slot with the draft
            return [
                SlotSet("email_response", draft),
                SlotSet("reply_stage", "review"),
                # Reset these slots to ensure clean state
                SlotSet("review_option", None),
                SlotSet("confirm_sending", None),
                SlotSet("confirm_edited_draft", None)
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
        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not found")
            return self._fallback_email_generation("", sender)
        
        # Extract recipient name from sender
        recipient_name = "there"
        if "(" in sender and ")" in sender:
            full_name = sender.split("(")[0].strip()
            recipient_name = full_name.split()[0] if full_name else "there"
        
        # Prepare the prompt
        prompt = f"""
        Generate a professional email reply to the following email:
        
        Original email subject: {subject}
        Original email sender: {sender}
        Original email content: 
        {original_content}
        
        Create a well-formatted, professional email that is concise, clear, and maintains appropriate tone.
        Focus on addressing the key points from the original email.
        Start with an appropriate greeting using the recipient's name if available.
        End with a professional sign-off.
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
                        {"role": "system", "content": "You are a helpful assistant that drafts professional emails."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.7
                },
                timeout=10
            )
            
            # Parse response
            response_data = response.json()
            email_text = response_data["choices"][0]["message"]["content"].strip()
            
            return email_text
            
        except Exception as e:
            logger.error(f"Error generating email with LLM: {e}")
            return self._fallback_email_generation("", sender)

    def generate_casual_reply(self, sender: str, subject: str, original_content: str) -> str:
        """Generate a casual, friendly reply based on the original email content."""
        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not found")
            return self._fallback_email_generation("", sender)
        
        # Extract recipient name from sender
        recipient_name = "there"
        if "(" in sender and ")" in sender:
            full_name = sender.split("(")[0].strip()
            recipient_name = full_name.split()[0] if full_name else "there"
        
        # Prepare the prompt
        prompt = f"""
        Generate a casual, friendly email reply to the following email:
        
        Original email subject: {subject}
        Original email sender: {sender}
        Original email content: 
        {original_content}
        
        Create a warm, conversational email that feels personal and informal while still being respectful.
        Use a friendly greeting with the recipient's first name if available.
        End with a casual sign-off.
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
                        {"role": "system", "content": "You are a helpful assistant that drafts friendly emails."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.8
                },
                timeout=10
            )
            
            # Parse response
            response_data = response.json()
            email_text = response_data["choices"][0]["message"]["content"].strip()
            
            return email_text
            
        except Exception as e:
            logger.error(f"Error generating email with LLM: {e}")
            return self._fallback_email_generation("", sender)

    def generate_custom_reply(self, style: str, sender: str, subject: str, original_content: str) -> str:
        """Generate a reply in a custom style specified by the user."""
        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not found")
            return self._fallback_email_generation("", sender)
        
        # Extract recipient name from sender
        recipient_name = "there"
        if "(" in sender and ")" in sender:
            full_name = sender.split("(")[0].strip()
            recipient_name = full_name.split()[0] if full_name else "there"
        
        # Prepare the prompt
        prompt = f"""
        Generate an email reply in a {style} style to the following email:
        
        Original email subject: {subject}
        Original email sender: {sender}
        Original email content: 
        {original_content}
        
        Create a well-formatted email that embodies the {style} style requested by the user.
        Use an appropriate greeting and sign-off that fits the requested style.
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
                        {"role": "system", "content": f"You are a helpful assistant that drafts emails in a {style} style."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 500,
                    "temperature": 0.7
                },
                timeout=10
            )
            
            # Parse response
            response_data = response.json()
            email_text = response_data["choices"][0]["message"]["content"].strip()
            
            return email_text
            
        except Exception as e:
            logger.error(f"Error generating email with LLM: {e}")
            return self._fallback_email_generation("", sender)
    
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

class ActionSendReply(Action):
    """Action to send the drafted email reply."""
    
    def name(self) -> Text:
        return "action_send_reply"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Send the drafted email reply.
        
        Args:
            dispatcher: Dispatcher to send messages to the user
            tracker: Tracker to get conversation state
            domain: Domain with parameters
            
        Returns:
            Empty list as this action doesn't update the conversation state
        """
        try:
            # Get email details from slots
            sender_full = tracker.get_slot("current_email_sender")
            subject = tracker.get_slot("current_email_subject")
            response = tracker.get_slot("email_response")
            email_id = tracker.get_slot("current_email_id")
            
            if not sender_full or not subject or not response:
                dispatcher.utter_message(
                    text="I don't have enough information to send a reply. Let's draft a response first."
                )
                return []
            
            # Extract email address from sender
            sender_match = re.search(r'\((.*?)\)', sender_full)
            sender_email = sender_match.group(1) if sender_match else sender_full
            
            # Initialize email client
            credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH")
            token_path = os.getenv("GMAIL_TOKEN_PATH")
            
            email_client = ImprovedEmailClient(
                credentials_path=credentials_path,
                token_path=token_path
            )
            
            # Add "Re:" prefix if not already present
            subject_prefix = "Re: " if not subject.startswith("Re:") else ""
            full_subject = f"{subject_prefix}{subject}"
            
            # Send the email
            success = email_client.send_email(
                to=sender_email,
                subject=full_subject,
                body=response,
                reply_to=email_id
            )
            
            # Let utter_email_sent handle the success message
            if not success:
                dispatcher.utter_message(
                    text="There was an issue sending your reply. Please check your internet connection and try again."
                )
            
            return []
            
        except Exception as e:
            logger.error(f"Error sending email reply: {str(e)}")
            dispatcher.utter_message(
                text="I encountered an error while sending your reply. Please try again later."
            )
            return []
        
class ActionEditReplyDraft(Action):
    """Action to handle email draft editing with improved understanding of edit requests."""
    
    def name(self) -> Text:
        return "action_edit_reply_draft"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Process user's edit request and update the draft accordingly.
        """
        try:
            # Get the current draft and the user's editing instructions
            current_draft = tracker.get_slot("email_response")
            edit_instruction = tracker.get_slot("user_input")
            
            if not current_draft:
                dispatcher.utter_message(
                    text="I don't have a draft to edit. Let's create one first."
                )
                return []
            
            if not edit_instruction:
                dispatcher.utter_message(
                    text="Please tell me what changes you'd like to make to the draft."
                )
                return [SlotSet("reply_stage", "editing")]
            
            # Apply the user's edits to the draft
            updated_draft = self.apply_edits_to_draft(current_draft, edit_instruction)
            
            # Display the updated draft
            draft_message = f"I've updated the draft with your edits:\n\n{updated_draft}\n\n"
            draft_message += "Would you like to:\n"
            draft_message += "1. Send this draft\n"
            draft_message += "2. Make more edits\n"
            draft_message += "3. Start over\n"
            draft_message += "4. Cancel"
            
            dispatcher.utter_message(text=draft_message)
            
            # Update the email_response slot with the edited draft
            return [
                SlotSet("email_response", updated_draft),
                SlotSet("reply_stage", "review_edited"),
                # Reset the user_input slot to capture the next instruction
                SlotSet("user_input", None),
                SlotSet("confirm_edited_draft", None)
            ]
            
        except Exception as e:
            logger.error(f"Error editing reply draft: {str(e)}")
            dispatcher.utter_message(
                text="I encountered an error while editing your draft. Please try again with clearer instructions."
            )
            return []
    
    def apply_edits_to_draft(self, current_draft: str, edit_instruction: str) -> str:
        """
        Apply user's editing instructions to the current draft.
        Uses LLM to understand complex edit requests.
        
        Args:
            current_draft: The current email draft text
            edit_instruction: The user's editing instructions
            
        Returns:
            Updated draft text with the requested changes
        """
        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not found")
            # Instead of using a fallback method, simply inform the user through UI
            dispatcher.utter_message(text="I'm having trouble applying your edits right now. Please try describing the changes differently or try again later.")
            return current_draft
        
        # Extract key information from the edit instruction
        edit_type = self._categorize_edit_instruction(edit_instruction)
        
        # Prepare the prompt based on the edit type
        prompt = f"""
        Original email draft:
        ```
        {current_draft}
        ```
        
        Edit instruction from user:
        ```
        {edit_instruction}
        ```
        
        Please edit the email draft according to the user's instructions. Preserve the general structure 
        (greeting, body, closing) and professional tone. Only make changes that align with the user's request.
        
        Return the complete edited email.
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
                        {"role": "system", "content": "You are a helpful assistant that edits email drafts."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 1000,
                    "temperature": 0.3
                },
                timeout=10
            )
            
            # Parse response
            response_data = response.json()
            edited_draft = response_data["choices"][0]["message"]["content"].strip()
            
            # Remove any markdown formatting that might be included
            edited_draft = re.sub(r'```email\n|```\n|```email|```', '', edited_draft)
            
            return edited_draft
            
        except Exception as e:
            logger.error(f"Error editing draft with LLM: {e}")
            
            # Instead of using a fallback method, we'll add a note to the draft
            error_note = "[NOTE: I couldn't fully apply your edit. Please provide clearer instructions or try again.]\n\n"
            return error_note + current_draft
    
    def _categorize_edit_instruction(self, edit_instruction: str) -> str:
        """
        Categorize the type of edit requested.
        
        Args:
            edit_instruction: The user's editing instructions
            
        Returns:
            Category of edit: 'add', 'remove', 'change', 'format'
        """
        edit_instruction = edit_instruction.lower()
        
        if any(word in edit_instruction for word in ["add", "include", "insert", "mention"]):
            return "add"
        elif any(word in edit_instruction for word in ["remove", "delete", "take out"]):
            return "remove"
        elif any(word in edit_instruction for word in ["change", "replace", "modify", "instead", "prefer"]):
            return "change"
        elif any(word in edit_instruction for word in ["format", "style", "tone", "make it"]):
            return "format"
        else:
            return "general"
    
    def _fallback_edit_draft(self, current_draft: str, edit_instruction: str) -> str:
        """
        Enhanced fallback method that provides transparency when unable to apply edits.
        
        Args:
            current_draft: Current email draft text
            edit_instruction: User's editing instructions
            
        Returns:
            Draft with the user's instructions appended as an editing note
        """
        # Add the editing instruction as a note at the top of the draft
        editing_note = f"[EDITING NOTE: {edit_instruction}]\n\n"
        
        # Log that we're using the fallback method
        logger.info(f"Using fallback edit method for instruction: {edit_instruction}")
        
        # Return the original draft with the editing note
        return editing_note + current_draft