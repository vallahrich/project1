"""
Enhanced actions for organizing and labeling emails.
"""

from typing import Any, Text, Dict, List
import os
import requests
import json
import logging

from rasa_sdk import Action, Tracker
from rasa_sdk.events import SlotSet
from rasa_sdk.executor import CollectingDispatcher

from actions.improved_email_client import ImprovedEmailClient

# Set up logger
logger = logging.getLogger(__name__)

class ActionGetLabelSuggestions(Action):
    """Action to get label suggestions for the current email."""
    
    def name(self) -> Text:
        return "action_get_label_suggestions"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Get suggested labels for the current email and display existing labels.
        """
        try:
            # Get email content for analysis
            content = tracker.get_slot("current_email_content")
            subject = tracker.get_slot("current_email_subject")
            email_id = tracker.get_slot("current_email_id")
            
            if not email_id or not content or not subject:
                dispatcher.utter_message(
                    text="I need an email selected to suggest labels. Let's check your inbox first."
                )
                return []
            
            # Initialize email client
            credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH")
            token_path = os.getenv("GMAIL_TOKEN_PATH")
            
            email_client = ImprovedEmailClient(
                credentials_path=credentials_path,
                token_path=token_path
            )
            
            # Get existing labels
            existing_labels = email_client.get_all_labels()
            
            # Use LLM to determine suggested labels
            suggested_labels = self.determine_labels(content, subject)
            
            # Format the response
            response = f"Based on the content, I'd recommend labeling this email as \"{suggested_labels[0]}\"" 
            if len(suggested_labels) > 1:
                response += f" or \"{suggested_labels[1]}\""
            response += ".\n\n"
            
            # Add existing labels
            if existing_labels:
                response += "Your existing labels:\n"
                for i, label in enumerate(existing_labels, 1):
                    if i <= 10:  # Limit to 10 labels to avoid too long messages
                        response += f"{i}. {label['name']}\n"
                
                if len(existing_labels) > 10:
                    response += f"...and {len(existing_labels) - 10} more\n"
                
                response += "\nYou can:\n"
                response += "- Select a number to apply an existing label\n"
                response += "- Type a new label name to create it\n"
                response += "- Say \"use recommendation\" to apply my suggested label\n"
            else:
                response += "\nYou don't have any custom labels yet. You can:\n"
                response += "- Type a new label name to create it\n"
                response += "- Say \"use recommendation\" to apply my suggested label\n"
            
            dispatcher.utter_message(text=response)
            
            # Store suggested labels in slot
            return [
                SlotSet("suggested_labels", suggested_labels),
                SlotSet("existing_labels", json.dumps([label["name"] for label in existing_labels]))
            ]
            
        except Exception as e:
            logger.error(f"Error getting label suggestions: {str(e)}")
            dispatcher.utter_message(
                text="I encountered an error while suggesting labels. Please try again later."
            )
            return []
    
    def determine_labels(self, content: str, subject: str) -> List[str]:
        """
        Use an external LLM service to determine appropriate labels for the email.
        Returns multiple suggestions.
        """
        # Use OpenAI API directly - best practice for external API calls in actions
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not found")
            return self._fallback_label_determination(content, subject)
        
        # Prepare the prompt
        prompt = f"""
        Analyze the following email and determine the most appropriate 2-3 category labels for it.
        Choose from these common categories: Work, Personal, Finance, Travel, Social, Updates, Important, Family, Shopping, or Promotions.
        If none of these fit well, suggest concise category names that best describe the email's purpose.
        
        Email subject: {subject}
        
        Email content:
        {content[:500]}  # Limit content length to avoid token issues
        
        Return only a JSON array of 2-3 category names without any explanation or additional text.
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
                        {"role": "system", "content": "You are a helpful assistant that labels emails."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 100,
                    "temperature": 0.3
                },
                timeout=10
            )
            
            # Parse response
            response_data = response.json()
            label_text = response_data["choices"][0]["message"]["content"].strip()
            
            # Try to parse as JSON
            try:
                labels = json.loads(label_text)
                if isinstance(labels, list) and all(isinstance(item, str) for item in labels):
                    return labels[:3]  # Limit to 3 labels
            except:
                # If JSON parsing fails, try to extract manually
                labels = [label.strip(' "\'[]') for label in label_text.split(',')]
                return [label for label in labels if label][:3]
            
            # Fallback if parsing fails
            return self._fallback_label_determination(content, subject)
            
        except Exception as e:
            logger.error(f"Error determining labels with LLM: {e}")
            return self._fallback_label_determination(content, subject)
    
    def _fallback_label_determination(self, content: str, subject: str) -> List[str]:
        """
        Fallback method for label determination using rule-based approach.
        """
        # Combine subject and body for analysis
        combined_text = (subject + " " + content).lower()
        
        labels = []
        
        if any(word in combined_text for word in ["meeting", "project", "deadline", "report"]):
            labels.append("Work")
        if any(word in combined_text for word in ["invoice", "payment", "receipt", "transaction"]):
            labels.append("Finance")
        if any(word in combined_text for word in ["urgent", "important", "immediately", "asap"]):
            labels.append("Important")
        if any(word in combined_text for word in ["flight", "hotel", "booking", "reservation"]):
            labels.append("Travel")
        if any(word in combined_text for word in ["newsletter", "update", "news"]):
            labels.append("Updates")
        
        # Add default if no matches
        if not labels:
            labels.append("General")
        
        return labels

class ActionApplySelectedLabel(Action):
    """Action to apply a selected or new label to the current email."""
    
    def name(self) -> Text:
        return "action_apply_selected_label"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Apply a user-selected label or create and apply a new one.
        """
        try:
            # Get the selected label or new label name
            label_choice = tracker.get_slot("label_choice")
            email_id = tracker.get_slot("current_email_id")
            
            if not email_id:
                dispatcher.utter_message(
                    text="I don't have an email selected to label. Let's check your inbox first."
                )
                return []
            
            if not label_choice:
                dispatcher.utter_message(
                    text="I didn't catch which label you want to apply. Please specify a label name or select from the existing ones."
                )
                return []
            
            # Get suggested and existing labels from slots
            suggested_labels = tracker.get_slot("suggested_labels") or []
            existing_labels_json = tracker.get_slot("existing_labels")
            existing_labels = json.loads(existing_labels_json) if existing_labels_json else []
            
            # Determine which label to apply
            label_to_apply = None
            
            # Check if using recommendation
            if label_choice.lower() in ["use recommendation", "use suggested", "use suggestion", "apply recommendation"]:
                if suggested_labels and len(suggested_labels) > 0:
                    label_to_apply = suggested_labels[0]
            
            # Check if selecting by number
            elif label_choice.isdigit() and 1 <= int(label_choice) <= len(existing_labels):
                label_to_apply = existing_labels[int(label_choice) - 1]
            
            # Otherwise use as new label name
            else:
                label_to_apply = label_choice
            
            # Initialize email client
            credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH")
            token_path = os.getenv("GMAIL_TOKEN_PATH")
            
            email_client = ImprovedEmailClient(
                credentials_path=credentials_path,
                token_path=token_path
            )
            
            # Apply the label
            success = email_client.apply_label(email_id, label_to_apply)
            
            if not success:
                dispatcher.utter_message(text=f"There was an issue applying the label '{label_to_apply}'.")
                return []
            
            # Check if this was a new label or existing
            if label_to_apply in existing_labels:
                message = f"I've applied the existing label '{label_to_apply}' to this email."
            elif label_to_apply in suggested_labels:
                message = f"I've applied the suggested label '{label_to_apply}' to this email."
            else:
                message = f"I've created and applied the new label '{label_to_apply}' to this email."
            
            dispatcher.utter_message(text=message)
            
            # Offer next actions
            options = "What would you like to do next?\n"
            options += "1. Apply another label\n"
            options += "2. Return to email\n"
            options += "3. Return to inbox\n"
            options += "4. Delete this email"
            
            dispatcher.utter_message(text=options)
            
            return []
            
        except Exception as e:
            logger.error(f"Error applying label: {str(e)}")
            dispatcher.utter_message(
                text="I encountered an error while applying the label. Please try again later."
            )
            return []