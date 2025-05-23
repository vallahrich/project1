"""
Enhanced Gmail API client wrapper for better email content extraction.
"""

import os
import base64
import json
import re
import html
from typing import List, Dict, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class ImprovedEmailClient:
    """An enhanced Gmail API client with better email content extraction"""
    
    # Gmail API scopes
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.labels'
    ]
    
    def __init__(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None):
        """Initialize with same parameters as original EmailClient"""
        self.credentials_path = credentials_path or os.getenv("GMAIL_CREDENTIALS_PATH") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            "credentials", 
            "gmail_credentials.json"
        )
        
        self.token_path = token_path or os.getenv("GMAIL_TOKEN_PATH") or os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "credentials",
            "gmail_token.json"
        )
        
        os.makedirs(os.path.dirname(self.token_path), exist_ok=True)
        
        self.service = None
        self.authorized = False
        self.user_id = 'me'
        
        # Connect to Gmail API
        self.connect()
    
    def connect(self) -> bool:
        """Connect to Gmail API using OAuth 2.0."""
        creds = None
        
        # Check if token file exists
        if os.path.exists(self.token_path):
            try:
                creds = Credentials.from_authorized_user_info(
                    json.loads(open(self.token_path).read()),
                    self.SCOPES
                )
            except Exception as e:
                print(f"Error loading token: {e}")
        
        # If credentials don't exist or are invalid, go through the OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Error refreshing token: {e}")
                    creds = None
            
            # If still no valid credentials, go through OAuth flow
            if not creds:
                if not self.credentials_path or not os.path.exists(self.credentials_path):
                    print("Credentials file not found")
                    return False
                
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(
                        self.credentials_path, self.SCOPES)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    print(f"Error during OAuth flow: {e}")
                    return False
                
                # Save the credentials for future use
                with open(self.token_path, 'w') as token:
                    token.write(creds.to_json())
        
        try:
            # Build the Gmail service
            self.service = build('gmail', 'v1', credentials=creds)
            self.authorized = True
            print("Successfully connected to Gmail API")
            return True
        except Exception as e:
            print(f"Failed to build Gmail service: {e}")
            return False
    
    @staticmethod
    def rate_limit(max_per_second):
        """Rate limiting decorator to prevent API throttling."""
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

    @rate_limit(2)  # 2 calls per second max
    def get_unread_emails(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """Enhanced version that retrieves emails with better content extraction"""
        if not self.authorized or not self.service:
            print("Not authorized to access Gmail")
            return []
        
        try:
            # Query for unread messages in inbox
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
                
                # Get the full message details with format='full' for complete content
                msg = self.service.users().messages().get(
                    userId=self.user_id, 
                    id=msg_id,
                    format='full'
                ).execute()
                
                headers = msg['payload']['headers']
                
                # Extract email details from headers
                subject = ""
                sender = ""
                sender_name = ""
                date_str = ""
                
                for header in headers:
                    if header['name'] == 'Subject':
                        subject = header['value']
                    elif header['name'] == 'From':
                        sender_full = header['value']
                        # Extract name and email address with better parsing
                        sender_name, sender = self._parse_sender(sender_full)
                    elif header['name'] == 'Date':
                        date_str = header['value']
                
                # Get the message body with enhanced extraction
                body = self._get_message_body_enhanced(msg)
                
                # Parse date into friendly format
                try:
                    date_obj = datetime.strptime(date_str.split('(')[0].strip(), "%a, %d %b %Y %H:%M:%S %z")
                    friendly_date = date_obj.strftime("%b %d, %Y at %I:%M %p")
                except Exception:
                    friendly_date = "Recently"
                
                # Create email object with enhanced fields
                email = {
                    "id": msg_id,
                    "sender": sender,
                    "sender_name": sender_name,
                    "subject": subject,
                    "snippet": msg.get('snippet', ''),
                    "body": body,
                    "date": friendly_date,
                    "labels": msg.get('labelIds', []),
                    "read": 'UNREAD' not in msg.get('labelIds', [])
                }
                
                emails.append(email)
            
            return emails
        
        except HttpError as error:
            print(f"An error occurred: {error}")
            return []
    
    def _parse_sender(self, sender_full: str) -> tuple:
        """Enhanced sender parsing to handle various formats"""
        if not sender_full:
            return "", ""
        
        # Handle different sender formats
        if '<' in sender_full and '>' in sender_full:
            # Format: "Name <email@domain.com>"
            parts = sender_full.split('<')
            sender_name = parts[0].strip().strip('"\'')
            sender_email = parts[1].split('>')[0].strip()
        elif '@' in sender_full and '<' not in sender_full:
            # Format: "email@domain.com"
            sender_email = sender_full.strip()
            sender_name = sender_email.split('@')[0]  # Use part before @ as name
        else:
            # Fallback
            sender_name = sender_full
            sender_email = sender_full
        
        return sender_name, sender_email
    
    def _get_message_body_enhanced(self, message: Dict[str, Any]) -> str:
        """Enhanced message body extraction with better handling of different formats"""
        body = ""
        
        try:
            payload = message.get('payload', {})
            
            # Handle multipart messages
            if 'parts' in payload:
                body = self._extract_from_parts(payload['parts'])
            
            # Handle simple messages
            elif 'body' in payload and 'data' in payload['body']:
                try:
                    body = base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
                except Exception as e:
                    print(f"Error decoding message body: {e}")
                    body = message.get('snippet', '')
            
            # Fallback to snippet if no body found
            if not body:
                body = message.get('snippet', '')
            
            # Clean up the body
            body = self._clean_body(body)
            
        except Exception as e:
            print(f"Error extracting message body: {e}")
            body = message.get('snippet', 'Error extracting message content')
        
        return body
    
    def _extract_from_parts(self, parts: List[Dict[str, Any]]) -> str:
        """Recursively extract text from message parts"""
        body = ""
        
        for part in parts:
            mime_type = part.get('mimeType', '')
            
            # Prefer plain text content
            if mime_type == 'text/plain':
                if 'body' in part and 'data' in part['body']:
                    try:
                        decoded = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        body = decoded
                        break  # Found plain text, use it
                    except Exception as e:
                        print(f"Error decoding plain text part: {e}")
            
            # Handle HTML content if no plain text found
            elif mime_type == 'text/html' and not body:
                if 'body' in part and 'data' in part['body']:
                    try:
                        decoded = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                        body = self._html_to_text(decoded)
                    except Exception as e:
                        print(f"Error decoding HTML part: {e}")
            
            # Handle nested parts recursively
            elif 'parts' in part:
                nested_body = self._extract_from_parts(part['parts'])
                if nested_body and not body:
                    body = nested_body
        
        return body
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML content to plain text"""
        try:
            # Remove HTML tags using regex (basic approach)
            text = re.sub(r'<[^>]+>', '', html_content)
            # Decode HTML entities
            text = html.unescape(text)
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)
            return text.strip()
        except Exception as e:
            print(f"Error converting HTML to text: {e}")
            return html_content
    
    def _clean_body(self, body: str) -> str:
        """Clean up email body content"""
        if not body:
            return ""
        
        # Remove excessive whitespace and line breaks
        cleaned = re.sub(r'\n\s*\n\s*\n+', '\n\n', body)
        
        # Remove unicode characters that don't display well
        cleaned = re.sub(r'[\u034f\u200c\u200b\u200d\u200e\u200f]+', '', cleaned)
        
        # Clean up excessive spaces
        cleaned = re.sub(r'[ \t]+', ' ', cleaned)
        
        # Remove common email artifacts
        cleaned = re.sub(r'=\d{2}', '', cleaned)  # Remove quoted-printable artifacts
        
        # Normalize line endings
        cleaned = cleaned.replace('\r\n', '\n').replace('\r', '\n')
        
        return cleaned.strip()
    
    def get_all_labels(self) -> List[Dict[str, Any]]:
        """Get all available labels in the user's Gmail account."""
        if not self.authorized or not self.service:
            print("Not authorized to access labels")
            return []
        
        try:
            results = self.service.users().labels().list(userId=self.user_id).execute()
            labels = results.get('labels', [])
            
            formatted_labels = []
            for label in labels:
                # Skip system labels
                if not label['id'].startswith('CATEGORY_') and not label['id'] in ['INBOX', 'SENT', 'SPAM', 'TRASH', 'DRAFT', 'UNREAD']:
                    formatted_labels.append({
                        'id': label['id'],
                        'name': label['name']
                    })
            
            return formatted_labels
        
        except HttpError as error:
            print(f"An error occurred: {error}")
            return []
    
    def send_email(self, to: str, subject: str, body: str, reply_to: Optional[str] = None) -> bool:
        """Send an email."""
        if not self.authorized or not self.service:
            print("Not authorized to send email")
            return False
        
        try:
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            
            if reply_to:
                message['In-Reply-To'] = reply_to
                message['References'] = reply_to
            
            msg = MIMEText(body)
            message.attach(msg)
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            self.service.users().messages().send(
                userId=self.user_id,
                body={'raw': raw_message}
            ).execute()
            
            return True
        
        except HttpError as error:
            print(f"An error occurred: {error}")
            return False
    
    def apply_label(self, email_id: str, label: str) -> bool:
        """Apply a label to an email."""
        if not self.authorized or not self.service:
            print("Not authorized to apply labels")
            return False
        
        try:
            label_id = self._get_or_create_label(label)
            
            if not label_id:
                return False
            
            self.service.users().messages().modify(
                userId=self.user_id,
                id=email_id,
                body={'addLabelIds': [label_id]}
            ).execute()
            
            return True
        
        except HttpError as error:
            print(f"An error occurred: {error}")
            return False
    
    def _get_or_create_label(self, label_name: str) -> Optional[str]:
        """Get the ID of a label, creating it if it doesn't exist."""
        try:
            results = self.service.users().labels().list(userId=self.user_id).execute()
            labels = results.get('labels', [])
            
            for label in labels:
                if label['name'].lower() == label_name.lower():
                    return label['id']
            
            new_label = self.service.users().labels().create(
                userId=self.user_id,
                body={'name': label_name}
            ).execute()
            
            return new_label['id']
        
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None
    
    def trash_email(self, email_id: str) -> bool:
        """Move an email to trash."""
        if not self.authorized or not self.service:
            print("Not authorized to trash emails")
            return False
            
        try:
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
            print(f"An error occurred: {error}")
            return False
        
    def mark_as_read(self, email_id: str) -> bool:
        """Mark an email as read by removing the UNREAD label."""
        if not self.authorized or not self.service:
            print("Not authorized to modify emails")
            return False
            
        try:
            self.service.users().messages().modify(
                userId=self.user_id,
                id=email_id,
                body={
                    'removeLabelIds': ['UNREAD']
                }
            ).execute()
            
            return True
            
        except HttpError as error:
            print(f"An error occurred: {error}")
            return False