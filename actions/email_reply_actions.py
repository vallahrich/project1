"""
Actions for drafting and sending email replies.
"""

from typing import Any, Text, Dict, List
import os

from rasa_sdk import Action, RasaProTracker, RasaProSlot
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.llm import SingleStepLLMCommandGenerator  

from actions.email_client import EmailClient


class ActionDraftReply(Action):
    """Action to draft a reply to the current email."""
    
    def name(self) -> Text:
        return "action_draft_reply"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Draft a reply to the current email using the user's instructions.
        
        Args:
            dispatcher: Dispatcher to send messages to the user
            tracker: Tracker to get conversation state
            domain: Domain with parameters
            
        Returns:
            List of events with the updated email_response slot
        """
        # Get the user's response content
        response_content = tracker.get_slot("email_response")
        
        if not response_content:
            dispatcher.utter_message(
                text="I didn't catch what you want to say in your reply. Could you please tell me what you'd like to say?"
            )
            return []
        
        # Get email details from slots
        sender = tracker.get_slot("current_email_sender")
        subject = tracker.get_slot("current_email_subject")
        original_content = tracker.get_slot("current_email_content")
        
        if not sender or not subject or not original_content:
            dispatcher.utter_message(
                text="I don't have the original email details. Let's check your inbox first."
            )
            return []
        
        # Use LLM to draft a professional email response
        enhanced_response = self.generate_professional_email(
            response_content, 
            sender, 
            subject, 
            original_content
        )
        
        # Show the draft to the user - we don't need to display the draft here
        # as it will be shown by the utter_confirm_sending response
        # which uses the {email_response} slot
        
        # Update the email_response slot with the enhanced response
        return [SlotSet("email_response", enhanced_response)]
    
    def generate_professional_email(self, content: str, sender: str, subject: str, original_content: str) -> str:
        """
        Generate a professional email response using Rasa Pro's LLM integration.
        
        Args:
            content: User's instructions for the reply
            sender: Original email sender
            subject: Original email subject
            original_content: Original email content
            
        Returns:
            Formatted email response
        """
        # Create LLM command generator
        llm_generator = SingleStepLLMCommandGenerator()
        
        # Extract recipient name from sender
        recipient_name = "there"
        if "(" in sender and ")" in sender:
            full_name = sender.split("(")[0].strip()
            # Take first name only
            recipient_name = full_name.split()[0] if full_name else "there"
        
        # Prepare the prompt for the LLM
        llm_prompt = f"""
        Draft a professional email reply based on the following information:
        
        Original email subject: {subject}
        Original email sender: {sender}
        Original email content: 
        {original_content}
        
        User's response instructions: {content}
        
        Create a well-formatted, professional email that incorporates the user's instructions
        while maintaining appropriate tone and etiquette. The email should be concise but complete.
        Start with an appropriate greeting using the recipient's name if available.
        End with a professional sign-off.
        """
        
        try:
            # Generate the response using Rasa Pro's LLM integration
            llm_response = llm_generator.generate(llm_prompt)
            return llm_response.strip()
        except Exception as e:
            print(f"Error generating email with LLM: {e}")
            
            # Fallback to a basic template if LLM fails
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
        
        email_client = EmailClient(
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