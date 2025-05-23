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
                    text="Ich habe keine E-Mail ausgewählt, auf die ich antworten kann. Lass uns zuerst deinen Posteingang überprüfen."
                )
                return []
            
            # Extract sender name for personalization
            sender_name = sender.split('(')[0].strip() if '(' in sender else sender
            
            # Check if this is a no-reply address
            is_no_reply = any(term in sender.lower() for term in ["no-reply", "noreply", "do-not-reply", "donotreply"])
            if is_no_reply:
                warning = "⚠️ Dies scheint eine No-Reply-E-Mail-Adresse zu sein, die normalerweise keine Antworten akzeptiert.\n\n"
                dispatcher.utter_message(text=warning)

            return [SlotSet("reply_stage", "initiate")]

        except Exception as e:
            logger.error(f"Error initiating reply: {str(e)}")
            dispatcher.utter_message(
                text="Ich habe einen Fehler beim Einrichten Ihrer Antwort festgestellt. Bitte versuchen Sie es später erneut."
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
        Generate a reply draft based on user's choice and input.
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
            
            # Generate the appropriate reply based on the type, now always including user_input
            if reply_type == "user_content" and user_input:
                draft = self.generate_reply_from_user_content(
                    user_input, sender, subject, original_content
                )
            elif reply_type == "professional":
                draft = self.generate_professional_reply(
                    sender, subject, original_content, user_input
                )
            elif reply_type == "casual":
                draft = self.generate_casual_reply(
                    sender, subject, original_content, user_input
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
        Formatiere den Inhalt des Benutzers in eine professionelle E-Mail-Antwort:

        Original E-Mail-Betreff: {subject}
        Original E-Mail-Absender: {sender}

        Benutzerinhalt: {content}

        Erstelle eine gut formatierte E-Mail, die den Inhalt des Benutzers wörtlich verwendet.
        Füge eine angemessene Begrüßung und einen professionellen Abschluss hinzu.
        Füge keinen neuen Inhalt hinzu und ändere nicht die Nachricht des Benutzers.
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
    
    def generate_professional_reply(self, sender: str, subject: str, original_content: str, user_input: str = None) -> str:
        """Generate a professional reply based on the original email content and user's input."""
        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not found")
            return self._fallback_email_generation(user_input or "", sender)
        
        # Extract recipient name from sender
        recipient_name = "there"
        if "(" in sender and ")" in sender:
            full_name = sender.split("(")[0].strip()
            recipient_name = full_name.split()[0] if full_name else "there"
        
        # Prepare the prompt - now including user input
        prompt = f"""
        Erstelle eine professionelle E-Mail-Antwort auf die folgende E-Mail:

        Original E-Mail-Betreff: {subject}
        Original E-Mail-Absender: {sender}
        Original E-Mail-Inhalt:
        {original_content}

        Benutzerdefinierte Anweisungen oder Punkte, die berücksichtigt werden sollen:
        {user_input or "No specific instructions provided."}

        Erstelle eine gut formatierte, professionelle E-Mail, die prägnant, klar und im angemessenen Ton gehalten ist.
        Gehe auf die Hauptpunkte der ursprünglichen E-Mail und alle spezifischen Punkte ein, die vom Benutzer erwähnt wurden.
        Beginne mit einer angemessenen Begrüßung unter Verwendung des Namens des Empfängers, wenn verfügbar.
        Beende die E-Mail mit einem professionellen Abschluss.
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
            return self._fallback_email_generation(user_input or "", sender)

    def generate_casual_reply(self, sender: str, subject: str, original_content: str, user_input: str = None) -> str:
        """Generate a casual, friendly reply based on the original email content and user's input."""
        # Get API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not found")
            return self._fallback_email_generation(user_input or "", sender)
        
        # Extract recipient name from sender
        recipient_name = "there"
        if "(" in sender and ")" in sender:
            full_name = sender.split("(")[0].strip()
            recipient_name = full_name.split()[0] if full_name else "there"
        
        # Prepare the prompt - now including user input
        prompt = f"""
        Erstelle eine informelle, freundliche E-Mail-Antwort auf die folgende E-Mail:

        Original E-Mail-Betreff: {subject}
        Original E-Mail-Absender: {sender}
        Original E-Mail-Inhalt:
        {original_content}

        Benutzerdefinierte Anweisungen oder Punkte, die berücksichtigt werden sollen:
        {user_input or "No specific instructions provided."}

        Erstelle eine warme, gesprächige E-Mail, die persönlich und informell wirkt und dennoch respektvoll bleibt.
        Gehe auf die Hauptpunkte der ursprünglichen E-Mail und alle spezifischen Punkte ein, die vom Benutzer erwähnt wurden.
        Verwende eine freundliche Begrüßung mit dem Vornamen des Empfängers, wenn verfügbar.
        Beende die E-Mail mit einem informellen Abschluss.
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
            return self._fallback_email_generation(user_input or "", sender)

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
        Erstelle eine E-Mail-Antwort im {style} Stil auf die folgende E-Mail:

        Original E-Mail-Betreff: {subject}
        Original E-Mail-Absender: {sender}
        Original E-Mail-Inhalt:
        {original_content}

        Erstelle eine gut formatierte E-Mail, die den vom Benutzer angeforderten {style} Stil verkörpert.
        Verwende eine angemessene Begrüßung und einen passenden Abschluss, der zum angeforderten Stil passt.
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
                        {"role": "system", "content": f"Du bist ein hilfreicher Assistent, der E-Mails im {style} Stil entwirft."},
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
        greeting = f"Hallo {recipient_name},"
        signature = "\n\nMit freundlichen Grüßen,\n[Your Name]"

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
                    text="Ich habe nicht genügend Informationen, um eine Antwort zu senden. Lass uns zuerst eine Antwort entwerfen."
                )
                return [
                    SlotSet("reply_stage", None),
                    SlotSet("review_option", None),
                    SlotSet("email_response", None),
                    SlotSet("confirm_edited_draft", None),
                    SlotSet("user_input", None)  # Add this to prevent previous inputs from reappearing
                ]
            
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
                    text="Es gab ein Problem beim Senden deiner Antwort. Bitte überprüfe deine Internetverbindung und versuche es erneut."
                )
            
                return [
                    SlotSet("reply_stage", None),
                    SlotSet("review_option", None),
                    SlotSet("email_response", None),
                    SlotSet("confirm_edited_draft", None)]
            logger.info("Email reply sent successfully.")
        except Exception as e:
            logger.error(f"Error sending email reply: {str(e)}")
            dispatcher.utter_message(
                text="Ich habe ein Problem beim Senden deiner Antwort festgestellt. Bitte versuche es später erneut."
            )
            return [
                SlotSet("reply_stage", None),
                SlotSet("review_option", None),
                SlotSet("email_response", None),
                SlotSet("confirm_edited_draft", None),
                SlotSet("user_input", None)  # Add this to prevent previous inputs from reappearing
            ]
        
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
                    text="Ich habe keinen Entwurf zum Bearbeiten. Lass uns zuerst einen erstellen."
                )
                return []
            
            if not edit_instruction:
                dispatcher.utter_message(
                    text="Bitte sag mir, welche Änderungen du am Entwurf vornehmen möchtest."
                )
                return [SlotSet("reply_stage", "editing")]
            
            # Apply the user's edits to the draft
            updated_draft = self.apply_edits_to_draft(current_draft, edit_instruction, dispatcher)
            
            # Display the updated draft
            draft_message = f"Ich habe den Entwurf mit deinen Änderungen aktualisiert:\n\n{updated_draft}\n\n"
            draft_message += "Möchtest du:\n"
            draft_message += "1. Diesen Entwurf senden\n"
            draft_message += "2. Weitere Änderungen vornehmen\n"
            draft_message += "3. Von vorne beginnen\n"
            draft_message += "4. Abbrechen"

            dispatcher.utter_message(text=draft_message)
            
            # Update the email_response slot with the edited draft
            return [
                SlotSet("email_response", updated_draft),
                SlotSet("reply_stage", "review_edited"),
                # Reset the user_input slot to capture the next instruction
                SlotSet("user_input", None)
            ]
            
        except Exception as e:
            logger.error(f"Error editing reply draft: {str(e)}")
            dispatcher.utter_message(
                text="Ich habe ein Problem beim Bearbeiten deines Entwurfs festgestellt. Bitte versuche es erneut mit klareren Anweisungen."
            )
            return []
    
    def apply_edits_to_draft(self, current_draft: str, edit_instruction: str, dispatcher: CollectingDispatcher) -> str:
        """
        Apply user's editing instructions to the current draft with more sophisticated parsing.
        """
        # Extract parts of the email for easier editing
        parts = self._parse_email_parts(current_draft)
        
        # Check if this is a full replacement (longer text that seems like a complete email)
        if len(edit_instruction.strip().split()) > 20:
            if any(word in edit_instruction.lower() for word in ["dear", "hello", "hi", "greetings"]):
                return edit_instruction
        
        # Use the LLM for interpreting edit instructions
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            try:
                # Prepare a more detailed prompt for the LLM
                prompt = f"""
                Du hilfst dabei, einen E-Mail-Entwurf gemäß spezifischer Benutzeranweisungen zu bearbeiten.

                Original E-Mail-Entwurf:
                ```
                {current_draft}
                ```

                Users Änderungsanweisung:
                ```
                {edit_instruction}
                ```

                Bitte nimm NUR die in der Änderungsanweisung angegebenen Änderungen vor.
                Bewahre das E-Mail-Format mit Begrüßung, Textabschnitten und Signatur bei.
                Behalte den ursprünglichen Ton und Stil bei, es sei denn, es wird ausdrücklich um eine Änderung gebeten.
                Gib die vollständige bearbeitete E-Mail ohne Erklärungen oder Markdown-Formatierung zurück.
                """
                
                response = requests.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "gpt-4o-2024-11-20",
                        "messages": [
                            {"role": "system", "content": "DDu bist ein hilfreicher Assistent, der E-Mail-Entwürfe bearbeitet."},
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
                logger.error(f"Error using LLM for editing: {e}")
                # If the LLM approach fails, try some simple pattern matching
                return self._apply_simple_edits(current_draft, edit_instruction, parts)
        
        # If no API key, use simple pattern matching
        return self._apply_simple_edits(current_draft, edit_instruction, parts)

    def _apply_simple_edits(self, current_draft: str, edit_instruction: str, parts: Dict[str, str]) -> str:
        """Apply edits using simple pattern matching if LLM is unavailable."""
        instruction_lower = edit_instruction.lower()
        
        # Check for common edit patterns
        if "change greeting" in instruction_lower or "update greeting" in instruction_lower:
            # Try to extract the new greeting
            match = re.search(r'to\s+"([^"]+)"', edit_instruction)
            if match:
                parts["greeting"] = match.group(1)
                return self._reconstruct_email(parts)
        
        elif "add paragraph" in instruction_lower:
            # Extract what comes after "add paragraph"
            content_to_add = edit_instruction.split("add paragraph", 1)[1].strip()
            parts["body"] += f"\n\n{content_to_add}"
            return self._reconstruct_email(parts)
        
        # If no pattern matches, just return the original with the edit instruction appended
        # This ensures the user's edit gets included somehow
        return f"{current_draft}\n\n[Edit: {edit_instruction}]"

    def _parse_email_parts(self, email: str) -> Dict[str, str]:
        """Parse an email into its component parts for easier editing."""
        lines = email.strip().split('\n')
        parts = {"greeting": "", "body": "", "signature": ""}
        
        # Find greeting line
        greeting_idx = -1
        for i, line in enumerate(lines):
            if any(word in line.lower() for word in ["dear", "hello", "hi", "greetings"]):
                greeting_idx = i
                break
        
        if greeting_idx >= 0:
            parts["greeting"] = lines[greeting_idx]
            lines = lines[greeting_idx+1:]
        
        # Find signature section
        sig_idx = -1
        sig_markers = ["regards", "sincerely", "best", "thanks", "thank you", "cheers"]
        for i, line in enumerate(lines):
            if any(marker in line.lower() for marker in sig_markers):
                sig_idx = i
                break
        
        if sig_idx >= 0:
            parts["signature"] = "\n".join(lines[sig_idx:])
            parts["body"] = "\n".join(lines[:sig_idx]).strip()
        else:
            parts["body"] = "\n".join(lines).strip()
        
        return parts

    def _reconstruct_email(self, parts: Dict[str, str]) -> str:
        """Reconstruct an email from its component parts."""
        email = ""
        if parts["greeting"]:
            email += parts["greeting"] + "\n\n"
        
        if parts["body"]:
            email += parts["body"] + "\n\n"
        
        if parts["signature"]:
            email += parts["signature"]
        
        return email