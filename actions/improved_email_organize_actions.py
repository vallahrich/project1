"""
Erweiterte Actions zum Organisieren und Beschriften von E-Mails.
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

# Logger einrichten
logger = logging.getLogger(__name__)


class ActionGetLabelSuggestions(Action):
    """Action, um Label-Vorschläge für die aktuelle E-Mail abzurufen."""
    
    def name(self) -> Text:
        return "action_get_label_suggestions"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Ruft vorgeschlagene Labels für die aktuelle E-Mail ab und zeigt vorhandene Labels an.
        """
        try:
            # E-Mail-Inhalt für Analyse abrufen
            content = tracker.get_slot("current_email_content")
            subject = tracker.get_slot("current_email_subject")
            email_id = tracker.get_slot("current_email_id")
            
            if not email_id or not content or not subject:
                dispatcher.utter_message(
                    text="Bitte wähle zuerst eine E-Mail aus, bevor ich Labels vorschlage."
                )
                return []
            
            # E-Mail-Client initialisieren
            credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH")
            token_path = os.getenv("GMAIL_TOKEN_PATH")
            
            email_client = ImprovedEmailClient(
                credentials_path=credentials_path,
                token_path=token_path
            )
            
            # Vorhandene Labels abrufen
            existing_labels = email_client.get_all_labels()
            
            # Vorschläge per LLM ermitteln
            suggested_labels = self.determine_labels(content, subject)
            
            # Antwort formatieren
            response = f"Basierend auf dem Inhalt empfehle ich das Label \"{suggested_labels[0]}\""
            if len(suggested_labels) > 1:
                response += f" oder \"{suggested_labels[1]}\""
            response += ".\n\n"
            
            # Vorhandene Labels hinzufügen
            if existing_labels:
                response += "Deine vorhandenen Labels:\n"
                for i, label in enumerate(existing_labels, 1):
                    if i <= 10:
                        response += f"{i}. {label['name']}\n"
                if len(existing_labels) > 10:
                    response += f"...und {len(existing_labels) - 10} weitere\n"
                response += "\nDu kannst:\n"
                response += "- Eine Nummer auswählen, um ein vorhandenes Label anzuwenden\n"
                response += "- Einen neuen Label-Namen eingeben, um ihn zu erstellen\n"
                response += "- \"Empfehlung verwenden\" sagen, um mein vorgeschlagenes Label anzuwenden\n"
            else:
                response += "\nDu hast noch keine benutzerdefinierten Labels. Du kannst:\n"
                response += "- Einen neuen Label-Namen eingeben, um ihn zu erstellen\n"
                response += "- \"Empfehlung verwenden\" sagen, um mein vorgeschlagenes Label anzuwenden\n"
            
            dispatcher.utter_message(text=response)
            
            # Vorschläge in Slots speichern
            return [
                SlotSet("suggested_labels", suggested_labels),
                SlotSet("existing_labels", json.dumps([label["name"] for label in existing_labels]))
            ]
            
        except Exception as e:
            logger.error(f"Fehler beim Abrufen der Label-Vorschläge: {str(e)}")
            dispatcher.utter_message(
                text="Beim Vorschlagen der Labels ist ein Fehler aufgetreten. Bitte versuche es später erneut."
            )
            return []
    
    def determine_labels(self, content: str, subject: str) -> List[str]:
        """
        Verwendet einen externen LLM-Service, um passende Labels zu ermitteln.
        Gibt mehrere Vorschläge zurück.
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API-Schlüssel nicht gefunden")
            return self._fallback_label_determination(content, subject)
        
        prompt = f"""
        Analysiere die folgende E-Mail und ermittle 2-3 passende Kategorienamen.
        Wähle aus diesen: Arbeit, Persönlich, Finanzen, Reise, Soziales, Updates, Wichtig, Familie, Einkaufen oder Werbung.
        Falls keine davon passt, schlage prägnante Kategorienamen vor.
        
        Betreff: {subject}
        
        Inhalt:
        {content[:500]}
        
        Gib nur ein JSON-Array mit 2-3 Kategorienamen zurück, ohne Erklärung.
        """
        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-4o-2024-11-20",
                    "messages": [
                        {"role": "system", "content": "Du bist ein hilfreicher Assistent zum Labeln von E-Mails."},
                        {"role": "user", "content": prompt}
                    ],
                    "max_tokens": 100,
                    "temperature": 0.3
                },
                timeout=10
            )
            response_data = response.json()
            label_text = response_data["choices"][0]["message"]["content"].strip()
            try:
                labels = json.loads(label_text)
                if isinstance(labels, list) and all(isinstance(item, str) for item in labels):
                    return labels[:3]
            except:
                labels = [lbl.strip(' "\'[]') for lbl in label_text.split(',')]
                return [lbl for lbl in labels if lbl][:3]
            return self._fallback_label_determination(content, subject)
        except Exception as e:
            logger.error(f"Fehler beim Ermitteln der Labels mit LLM: {e}")
            return self._fallback_label_determination(content, subject)
    
    def _fallback_label_determination(self, content: str, subject: str) -> List[str]:
        """
        Fallback-Strategie zur Label-Ermittlung basierend auf Regeln.
        """
        combined_text = (subject + " " + content).lower()
        labels = []
        if any(w in combined_text for w in ["meeting", "project", "deadline", "report"]):
            labels.append("Arbeit")
        if any(w in combined_text for w in ["invoice", "payment", "receipt", "transaction"]):
            labels.append("Finanzen")
        if any(w in combined_text for w in ["urgent", "important", "immediately", "asap"]):
            labels.append("Wichtig")
        if any(w in combined_text for w in ["flight", "hotel", "booking", "reservation"]):
            labels.append("Reise")
        if any(w in combined_text for w in ["newsletter", "update", "news"]):
            labels.append("Updates")
        if not labels:
            labels.append("Allgemein")
        return labels


class ActionApplySelectedLabel(Action):
    """Action, um ein ausgewähltes oder neues Label auf die aktuelle E-Mail anzuwenden."""
    
    def name(self) -> Text:
        return "action_apply_selected_label"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        """
        Erstellt und/oder wendet ein Label auf die ausgewählte E-Mail an.
        """
        try:
            label_choice = tracker.get_slot("label_choice")
            email_id = tracker.get_slot("current_email_id")
            
            if not email_id:
                dispatcher.utter_message(
                    text="Es ist keine E-Mail ausgewählt. Lass uns zuerst deinen Posteingang prüfen."
                )
                return []
            if not label_choice:
                dispatcher.utter_message(
                    text="Ich habe nicht verstanden, welches Label du möchtest. Bitte gib einen Label-Namen ein oder wähle eines aus."
                )
                return []
            
            suggested_labels = tracker.get_slot("suggested_labels") or []
            existing_labels_json = tracker.get_slot("existing_labels")
            existing_labels = json.loads(existing_labels_json) if existing_labels_json else []
            
            label_to_apply = None
            if label_choice.lower() in ["empfehlung verwenden", "empfehlung"]:
                if suggested_labels:
                    label_to_apply = suggested_labels[0]
            elif label_choice.isdigit() and 1 <= int(label_choice) <= len(existing_labels):
                label_to_apply = existing_labels[int(label_choice) - 1]
            else:
                label_to_apply = label_choice
            
            credentials_path = os.getenv("GMAIL_CREDENTIALS_PATH")
            token_path = os.getenv("GMAIL_TOKEN_PATH")
            email_client = ImprovedEmailClient(
                credentials_path=credentials_path,
                token_path=token_path
            )
            
            success = email_client.apply_label(email_id, label_to_apply)
            
            if not success:
                dispatcher.utter_message(text=f"Fehler beim Anwenden des Labels '{label_to_apply}'.")
                return []
            
            if label_to_apply in existing_labels:
                message = f"Ich habe das vorhandene Label '{label_to_apply}' angewendet."
            elif label_to_apply in suggested_labels:
                message = f"Ich habe das vorgeschlagene Label '{label_to_apply}' angewendet."
            else:
                message = f"Ich habe das neue Label '{label_to_apply}' erstellt und angewendet."
            
            dispatcher.utter_message(text=message)
            
            options = "Was möchtest du als Nächstes tun?\n"
            options += "1. Weiteres Label anwenden\n"
            options += "2. Zurück zur E-Mail\n"
            options += "3. Zurück zum Posteingang\n"
            options += "4. Diese E-Mail löschen"
            
            dispatcher.utter_message(text=options)
            
            return []
        except Exception as e:
            logger.error(f"Fehler beim Anwenden des Labels: {str(e)}")
            dispatcher.utter_message(
                text="Beim Anwenden des Labels ist ein Fehler aufgetreten. Bitte versuche es später erneut."
            )
            return []
