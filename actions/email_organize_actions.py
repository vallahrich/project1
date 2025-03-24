"""
Actions for organizing and labeling emails.
"""

from typing import Any, Text, Dict, List
import os

from rasa_sdk import Action, RasaProTracker, RasaProSlot
from rasa_sdk.executor import CollectingDispatcher
# from rasa_sdk.llm import SingleStepLLMCommandGenerator

from actions.email_client import EmailClient


class ActionSortMail(Action):
    """Action to sort emails based on content analysis."""
    
    def name(self) -> Text:
        return "action_sort_mail"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: RasaProTracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Sort emails into categories based on content analysis.
        
        Args:
            dispatcher: Dispatcher to send messages to the user
            tracker: Tracker to get conversation state
            domain: Domain with parameters
            
        Returns:
            Empty list as this action doesn't update the conversation state
        """
        # Initialize email client
        credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH")
        token_path = os.getenv("GMAIL_TOKEN_PATH")
        
        email_client = EmailClient(
            credentials_path=credentials_path,
            token_path=token_path
        )
        
        dispatcher.utter_message(
            text="I'm organizing your emails based on their content. This might take a moment..."
        )
        
        # Sort emails using the content analysis algorithm
        success = email_client.sort_emails_by_content()
        
        # Let utter_sorting_complete handle the success message
        if not success:
            dispatcher.utter_message(
                text="I had trouble organizing your emails. Please check your internet connection and try again."
            )
        
        return []


class ActionLabelMail(Action):
    """Action to label the current email."""
    
    def name(self) -> Text:
        return "action_label_mail"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: RasaProTracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Label the current email, using AI to determine the label if none is provided.
        
        Args:
            dispatcher: Dispatcher to send messages to the user
            tracker: Tracker to get conversation state
            domain: Domain with parameters
            
        Returns:
            Empty list as this action doesn't update the conversation state
        """
        # Get the label from the slot
        label = tracker.get_slot("email_label")
        email_id = tracker.get_slot("current_email_id")
        
        if not email_id:
            dispatcher.utter_message(
                text="I don't have an email selected to label. Let's check your inbox first."
            )
            return []
        
        # Get email content for analysis if no label is provided
        if not label:
            content = tracker.get_slot("current_email_content")
            subject = tracker.get_slot("current_email_subject")
            
            if not content or not subject:
                dispatcher.utter_message(
                    text="I need more information about the email to determine an appropriate label."
                )
                return []
            
            # Use LLM to determine the appropriate label
            determined_label = self.determine_label(content, subject)
            label = determined_label
            
            # Tell the user what label was chosen
            dispatcher.utter_message(
                text=f"Based on the content, I've determined this email should be labeled as '{label}'."
            )
        
        # Initialize email client
        credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH")
        token_path = os.getenv("GMAIL_TOKEN_PATH")
        
        email_client = EmailClient(
            credentials_path=credentials_path,
            token_path=token_path
        )
        
        # Apply the label
        success = email_client.apply_label(email_id, label)
        
        # Let utter_labeling_complete handle the success message
        if not success:
            dispatcher.utter_message(text=f"There was an issue applying the label '{label}'.")
        
        return []
    
    def determine_label(self, content: str, subject: str) -> str:
        """
        Use Rasa Pro's LLM to determine an appropriate label for the email.
        
        Args:
            content: Email content
            subject: Email subject
            
        Returns:
            Appropriate label for the email
        """
        # Create LLM command generator
        llm_generator = SingleStepLLMCommandGenerator()
        
        # Prepare the prompt for the LLM
        llm_prompt = f"""
        Analyze the following email and determine the most appropriate category label for it.
        Choose from these common categories: Work, Personal, Finance, Travel, Social, Updates, Important, Family, Shopping, or Promotions.
        If none of these fit well, suggest a single concise category name that best describes the email's purpose.
        
        Email subject: {subject}
        
        Email content:
        {content[:500]}  # Limit content length to avoid token issues
        
        Return only the category name without any explanation or additional text.
        """
        
        try:
            # Generate the label using Rasa Pro's LLM integration
            label = llm_generator.generate(llm_prompt).strip()
            
            # Clean up the response - ensure it's just a single label
            if "\n" in label:
                label = label.split("\n")[0]
            
            return label
        except Exception as e:
            print(f"Error determining label with LLM: {e}")
            
            # Fallback to rule-based approach if LLM fails
            combined_text = (subject + " " + content).lower()
            
            if any(word in combined_text for word in ["meeting", "project", "deadline", "report"]):
                return "Work"
            elif any(word in combined_text for word in ["invoice", "payment", "receipt", "transaction"]):
                return "Finance"
            elif any(word in combined_text for word in ["urgent", "important", "immediately", "asap"]):
                return "Important"
            elif any(word in combined_text for word in ["flight", "hotel", "booking", "reservation"]):
                return "Travel"
            elif any(word in combined_text for word in ["newsletter", "update", "news"]):
                return "Updates"
            else:
                return "General"