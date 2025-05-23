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
                    text="Ich brauche eine ausgewählte E‑Mail, um Labels vorzuschlagen. Lass uns zuerst deinen Posteingang ansehen."
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
            response = f"Basierend auf dem Inhalt würde ich empfehlen, diese E‑Mail als \"{suggested_labels[0]}\" zu labeln."
            if len(suggested_labels) > 1:
                response += f" or \"{suggested_labels[1]}\""
            response += ".\n\n"

            # Add existing labels
            if existing_labels:
                response += "Deine vorhandenen Labels:\n"
                for i, label in enumerate(existing_labels, 1):
                    if i <= 10:  # Limit to 10 labels to avoid too long messages
                        response += f"{i}. {label['name']}\n"
                
                if len(existing_labels) > 10:
                    response += f"...und {len(existing_labels) - 10} weitere\n"

                response += "\nDu kannstn:\n"
                response += "- Wähle eine Nummer aus, um ein vorhandenes Label anzuwenden\n"
                response += "- Gib einen neuen Labelnamen ein, um ihn zu erstellen\n"
                response += "- Sage \"Verwendung der Empfehlung\", um mein vorgeschlagenes Label anzuwenden\n"
            else:
                response += "\nDu hast noch keine benutzerdefinierten Labels. Du kannst:\n"
                response += "- Gib einen neuen Labelnamen ein, um ihn zu erstellen\n"
                response += "- Sage \"Verwendung der Empfehlung\", um mein vorgeschlagenes Label anzuwenden\n"

            dispatcher.utter_message(text=response)

            # Store suggested labels in slot
            return [
                SlotSet("suggested_labels", suggested_labels),
                SlotSet("existing_labels", json.dumps([label["name"] for label in existing_labels]))
            ]

        except Exception as e:
            logger.error(f"Error getting label suggestions: {str(e)}")
            dispatcher.utter_message(
                text="Ich habe einen Fehler beim Vorschlagen von Labels festgestellt. Bitte versuche es später noch einmal."
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
        Analysiere die folgende E‑Mail und bestimme die passendsten 2-3 Kategorien dafür.
        Wähle aus diesen gängigen Kategorien: Arbeit, Privat, Finanzen, Reisen, Soziales, Updates, Wichtig, Familie, Einkaufen oder Werbung.
        Wenn keine dieser Kategorien gut passt, schlage prägnante Kategorienamen vor, die den Zweck der E‑Mail am besten beschreiben.

        E‑Mail-Betreff: {subject}

        E‑Mail-Inhalt:
        {content[:500]}  # Begrenze die Inhaltslänge, um Token-Probleme zu vermeiden

        Gib nur ein JSON-Array von 2-3 Kategorienamen ohne Erklärung oder zusätzlichen Text zurück.
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
                        {"role": "system", "content": "Du bist ein hilfreicher Assistent, der E‑Mails labelt."},
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
                    text="Ich habe keine E‑Mail ausgewählt, die ich labeln kann. Lass uns zuerst deinen Posteingang ansehen."
                )
                return []
            
            if not label_choice:
                dispatcher.utter_message(
                    text="Ich habe nicht mitbekommen, welches Label du anwenden möchtest. Bitte gib einen Labelnamen an oder wähle aus den vorhandenen aus."
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
                dispatcher.utter_message(text=f"Es gab ein Problem beim Anwenden des Labels '{label_to_apply}'.")
                return []

            # Check if this was a new label or existing
            if label_to_apply in existing_labels:
                message = f"Ich habe das vorhandene Label '{label_to_apply}' auf diese E‑Mail angewendet."
            elif label_to_apply in suggested_labels:
                message = f"Ich habe das vorgeschlagene Label '{label_to_apply}' auf diese E‑Mail angewendet."
            else:
                message = f"Ich habe das neue Label '{label_to_apply}' auf diese E‑Mail angewendet."

            dispatcher.utter_message(text=message)

            # Offer next actions
            options = "Was möchtest du als Nächstes tun?\n"
            options += "1. Ein weiteres Label anwenden\n"
            options += "2. Zurück zur E‑Mail\n"
            options += "3. Zurück zum Posteingang\n"
            options += "4. Diese E‑Mail löschen"

            dispatcher.utter_message(text=options)

            return []
            
        except Exception as e:
            logger.error(f"Error applying label: {str(e)}")
            dispatcher.utter_message(
                text="Ich habe einen Fehler beim Anwenden des Labels festgestellt. Bitte versuche es später noch einmal."
            )
            return []