"""
Gmail-API-Client-Wrapper für Chatbot-Integration.
Dieses Modul bietet eine einheitliche Schnittstelle zur Interaktion mit Gmail.
"""

import os
import base64
import json
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class EmailClient:
    """Ein Gmail-API-Client für den Rasa-Chatbot"""
    
    # Gmail-API-Berechtigungen
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.labels'
    ]
    
    def __init__(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None):
        """
        Initialisiert den Gmail-Client.
        
        Args:
            credentials_path: Pfad zur credentials.json-Datei
            token_path: Pfad zum Speichern/Laden der token.json-Datei
        """
        # Suche nach Anmeldedaten an mehreren Speicherorten mit Fallbacks
        self.credentials_path = credentials_path or os.getenv("GMAIL_CREDENTIALS_PATH") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "credentials", 
            "gmail_credentials.json"
        )
        
        # Token-Pfad mit sinnvollen Standardwerten festlegen
        self.token_path = token_path or os.getenv("GMAIL_TOKEN_PATH") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "credentials",
            "gmail_token.json"
        )
        
        # Sicherstellen, dass das Verzeichnis für das Token existiert
        os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
        
        self.service = None
        self.authorized = False
        self.user_id = 'me'  # Standardwert für authentifizierten Nutzer
        
        # Verbindung zur Gmail-API herstellen
        self.connect()
    
    def connect(self) -> bool:
        """
        Stellt eine Verbindung zur Gmail-API mittels OAuth 2.0 her.
        
        Returns:
            bool: True, wenn Verbindung erfolgreich, sonst False
        """
        creds = None
        
        # Prüfen, ob die Token-Datei existiert
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_info(
                    json.loads(open(self.token_path).read()),
                    self.SCOPES
                )
            except Exception as e:
                print(f"Fehler beim Laden des Tokens: {e}")
        
        # Wenn keine gültigen Anmeldedaten vorhanden sind, OAuth-Flow starten
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Fehler beim Aktualisieren des Tokens: {e}")
                    creds = None
            
            # Falls weiterhin keine gültigen Anmeldedaten, OAuth-Flow durchführen
            if not creds:
                if not self.credentials_path or not os.path.exists(self.credentials_path):
                    print("Credentials-Datei nicht gefunden")
                    return False
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print(f"Fehler beim OAuth-Flow: {e}")
                    return False
                
                # Speichern der Anmeldedaten für zukünftige Verwendung
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
        
        try:
            # Gmail-Service aufbauen
            self.service = build('gmail', 'v1', credentials=creds)
            self.authorized = True
            print("Erfolgreich mit der Gmail-API verbunden")
            return True
        except Exception as e:
            print(f"Fehler beim Erstellen des Gmail-Services: {e}")
            return False
    
    @staticmethod
    def rate_limit(max_per_second):
        """
        Decorator zur Ratenbegrenzung, um API-Drosselung zu vermeiden.
        
        Args:
            max_per_second: Maximale Anzahl Aufrufe pro Sekunde
        
        Returns:
            Die dekorierte Funktion mit Ratenbegrenzung
        """
        from functools import wraps
        import time
        
        min_interval = 1.0 / max_per_second
        last_called = [0.0]
        
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                elapsed = time.time() - last_called[0]
                left_to_wait = min_interval - elapsed
                
                if left_to_wait > 0:
                    time.sleep(left_to_wait)
                
                ret = func(*args, **kwargs)
                last_called[0] = time.time()
                return ret
            return wrapper
        return decorator

    @rate_limit(2)  # Maximal 2 Aufrufe pro Sekunde
    def get_unread_emails(self, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Holt ungelesene E-Mails aus dem Posteingang mit Ratenbegrenzung.
        
        Args:
            max_results: Maximale Anzahl an E-Mails zum Abrufen
        
        Returns:
            Liste von E-Mail-Objekten mit id, sender, subject, snippet, body und date
        """
        if not self.authorized or not self.service:
            print("Keine Berechtigung zum Zugriff auf Gmail")
            return []
        
        try:
            # Suche nach ungelesenen Nachrichten im Posteingang
            results = self.service.users().messages().list(
                userId=self.user_id,
                labelIds=['INBOX', 'UNREAD'],
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            
            if not messages:
                return []
            
            emails = []
            
            for message in messages:
                msg_id = message['id']
                
                # Detailierte Nachricht abrufen
                msg = self.service.users().messages().get(
                    userId=self.user_id, 
                    id=msg_id,
                    format='full'
                ).execute()
                
                headers = msg['payload']['headers']
                
                # E-Mail-Details aus den Headern extrahieren
                subject = ""
                sender = ""
                sender_name = ""
                date_str = ""
                
                for header in headers:
                    if header['name'] == 'Subject':
                        subject = header['value']
                    elif header['name'] == 'From':
                        sender_full = header['value']
                        # Name und Adresse trennen
                        if '<' in sender_full and '>' in sender_full:
                            sender_name = sender_full.split('<')[0].strip()
                            sender = sender_full.split('<')[1].split('>')[0].strip()
                        else:
                            sender = sender_full
                            sender_name = sender_full
                    elif header['name'] == 'Date':
                        date_str = header['value']
                
                # Nachrichtentext abrufen
                body = self._get_message_body(msg)
                
                # Datum parsen
                try:
                    date_obj = datetime.strptime(date_str.split('(')[0].strip(), "%a, %d %b %Y %H:%M:%S %z")
                    date_iso = date_obj.isoformat()
                except:
                    date_iso = datetime.now().isoformat()
                
                # E-Mail-Objekt erstellen
                email = {
                    "id": msg_id,
                    "sender": sender,
                    "sender_name": sender_name,
                    "subject": subject,
                    "snippet": msg.get('snippet', ''),
                    "body": body,
                    "date": date_iso
                }
                
                emails.append(email)
            
            return emails
        
        except HttpError as error:
            print(f"Ein Fehler ist aufgetreten: {error}")
            return []
    
    def _get_message_body(self, message: Dict[str, Any]) -> str:
        """
        Extrahiert den Nachrichtentext aus der Gmail-API-Antwort.
        
        Args:
            message: Das Nachricht-Objekt von der Gmail-API
        
        Returns:
            Den Nachrichtentext als String
        """
        body = ""
        
        if 'parts' in message['payload']:
            for part in message['payload']['parts']:
                if part['mimeType'] == 'text/plain':
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
                elif 'parts' in part:
                    for subpart in part['parts']:
                        if subpart['mimeType'] == 'text/plain':
                            body = base64.urlsafe_b64decode(subpart['body']['data']).decode('utf-8')
                            break
        elif 'body' in message['payload'] and 'data' in message['payload']['body']:
            body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
        
        return body
    
    def send_email(self, to: str, subject: str, body: str, reply_to: Optional[str] = None) -> bool:
        """
        Sendet eine E-Mail.
        
        Args:
            to: Empfänger-Adresse
            subject: Betreff der E-Mail
            body: Inhalt der E-Mail
            reply_to: Nachricht-ID, auf die geantwortet wird (optional)
        
        Returns:
            True wenn die E-Mail erfolgreich gesendet wurde, sonst False
        """
        if not self.authorized or not self.service:
            print("Keine Berechtigung zum Versenden von E-Mails")
            return False
        
        try:
            # E-Mail-Nachricht erstellen
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            
            # Antwort-Header hinzufügen, falls reply_to gesetzt ist
            if reply_to:
                message['In-Reply-To'] = reply_to
                message['References'] = reply_to
            
            # Nachrichtentext anhängen
            msg = MIMEText(body)
            message.attach(msg)
            
            # Kodierung der Nachricht
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Nachricht versenden
            self.service.users().messages().send(
                userId=self.user_id,
                body={'raw': raw_message}
            ).execute()
            
            return True
        
        except HttpError as error:
            print(f"Ein Fehler ist aufgetreten: {error}")
            return False
    
    def apply_label(self, email_id: str, label: str) -> bool:
        """
        Wendet ein Label auf eine E-Mail an.
        
        Args:
            email_id: Die ID der E-Mail
            label: Name des Labels
        
        Returns:
            True wenn das Label erfolgreich angewendet wurde, sonst False
        """
        if not self.authorized or not self.service:
            print("Keine Berechtigung zum Anwenden von Labels")
            return False
        
        try:
            # Label-ID ermitteln oder neu erstellen
            label_id = self._get_or_create_label(label)
            
            if not label_id:
                return False
            
            # Label auf die E-Mail anwenden
            self.service.users().messages().modify(
                userId=self.user_id,
                id=email_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            
            return True
        
        except HttpError as error:
            print(f"Ein Fehler ist aufgetreten: {error}")
            return False
    
    def _get_or_create_label(self, label_name: str) -> Optional[str]:
        """
        Ermittelt die ID eines Labels oder erstellt es, falls es nicht existiert.
        
        Args:
            label_name: Name des Labels
        
        Returns:
            Die Label-ID oder None bei Fehler
        """
        try:
            # Alle Labels abfragen
            results = self.service.users().labels().list(userId=self.user_id).execute()
            labels = results.get('labels', [])
            
            # Prüfen, ob Label bereits existiert
            for label in labels:
                if label['name'].lower() == label_name.lower():
                    return label['id']
            
            # Label neu erstellen, falls nicht vorhanden
            new_label = self.service.users().labels().create(
                userId=self.user_id,
                body={'name': label_name}
            ).execute()
            
            return new_label['id']
        
        except HttpError as error:
            print(f"Ein Fehler ist aufgetreten: {error}")
            return None
    
    def sort_emails_by_content(self) -> bool:
        """
        Sortiert E-Mails basierend auf Inhaltsanalyse in Kategorien.
        Nutzt einfache Schlüsselwort-Suche für die Kategorisierung.
        
        Returns:
            True wenn die E-Mails erfolgreich sortiert wurden, sonst False
        """
        if not self.authorized or not self.service:
            print("Keine Berechtigung zum Sortieren von E-Mails")
            return False
        
        try:
            # Aktuelle E-Mails abrufen (bis zu 50)
            results = self.service.users().messages().list(
                userId=self.user_id,
                labelIds=['INBOX'],
                maxResults=50
            ).execute()
            messages = results.get('messages', [])
            
            if not messages:
                return True  # Keine E-Mails zum Sortieren
            
            # Kategorien und Schlüsselwörter definieren
            categories = {
                'Arbeit': ['projekt', 'frist', 'besprechung', 'bericht', 'kunde', 'aufgabe'],
                'Finanzen': ['rechnung', 'zahlung', 'beleg', 'transaktion', 'abrechnung', 'abo'],
                'Reise': ['flug', 'hotel', 'buchung', 'reservierung', 'reiseplan', 'trip'],
                'Soziales': ['einladung', 'event', 'party', 'feier', 'treffen'],
                'Updates': ['newsletter', 'update', 'ankündigung', 'nachricht'],
                'Dringend': ['dringend', 'wichtig', 'sofort', 'asap', 'notfall']
            }
            
            # Sicherstellen, dass alle Kategorien-Labels existieren
            for category in categories:
                self._get_or_create_label(category)
            
            # E-Mails verarbeiten
            for message in messages:
                msg_id = message['id']
                
                # Vollständige Nachricht abrufen
                msg = self.service.users().messages().get(
                    userId=self.user_id, 
                    id=msg_id,
                    format='full'
                ).execute()
                
                # Betreff und Nachrichtentext extrahieren
                subject = ""
                for header in msg['payload']['headers']:
                    if header['name'] == 'Subject':
                        subject = header['value']
                        break
                body = self._get_message_body(msg)
                
                # Inhalt für Analyse kombinieren
                content = f"{subject} {body}".lower()
                
                # Kategorien ermitteln
                matched_categories = []
                for category, keywords in categories.items():
                    for keyword in keywords:
                        if keyword.lower() in content:
                            matched_categories.append(category)
                            break
                
                # Labels auf die E-Mail anwenden
                for category in matched_categories:
                    label_id = self._get_or_create_label(category)
                    if label_id:
                        self.service.users().messages().modify(
                            userId=self.user_id,
                            id=msg_id,
                            body={'addLabelIds': [label_id]}
                        ).execute()
            
            return True
        
        except HttpError as error:
            print(f"Ein Fehler ist aufgetreten: {error}")
            return False
    
    def trash_email(self, email_id: str) -> bool:
        """
        Verschiebt eine E-Mail in den Papierkorb.
        
        Args:
            email_id: ID der zu löschenden E-Mail
        
        Returns:
            True wenn erfolgreich, sonst False
        """
        if not self.authorized or not self.service:
            print("Keine Berechtigung zum Löschen von E-Mails")
            return False
            
        try:
            # In den Papierkorb verschieben durch Hinzufügen des TRASH-Labels und Entfernen von INBOX
            self.service.users().messages().modify(
                userId=self.user_id,
                id=email_id,
                body={
                    'addLabelIds': ['TRASH'],
                    'removeLabelIds': ['INBOX']
                }
            ).execute()
            
            return True
            
        except HttpError as error:
            print(f"Ein Fehler ist aufgetreten: {error}")
            return False
            
    def mark_as_read(self, email_id: str) -> bool:
        """
        Markiert eine E-Mail als gelesen, indem das UNREAD-Label entfernt wird.
        
        Args:
            email_id: ID der E-Mail
        
        Returns:
            True wenn erfolgreich, sonst False
        """
        if not self.authorized or not self.service:
            print("Keine Berechtigung zum Modifizieren von E-Mails")
            return False
            
        try:
            # UNREAD-Label entfernen
            self.service.users().messages().modify(
                userId=self.user_id,
                id=email_id,
                body={
                    'removeLabelIds': ['UNREAD']
                }
            ).execute()
            
            return True
            
        except HttpError as error:
            print(f"Ein Fehler ist aufgetreten: {error}")
            return False
