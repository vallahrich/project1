"""
Enhanced Gmail API client wrapper for improved email navigation and management.
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


class ImprovedEmailClient:
    """An enhanced Gmail API client for the Rasa chatbot with better navigation"""
    
    # Gmail API scopes
    SCOPES = [
        'https://www.googleapis.com/auth/gmail.readonly',
        'https://www.googleapis.com/auth/gmail.send',
        'https://www.googleapis.com/auth/gmail.modify',
        'https://www.googleapis.com/auth/gmail.labels'
    ]
    
    def __init__(self, credentials_path: Optional[str] = None, token_path: Optional[str] = None):
        """Initialize with same parameters as original EmailClient"""
        # Same initialization as the original EmailClient
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
        """
        Connect to Gmail API using OAuth 2.0.
        
        Returns:
            bool: True if connection successful, False otherwise
        """
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
        """
        Rate limiting decorator to prevent API throttling.
        
        Args:
            max_per_second: Maximum number of calls allowed per second
            
        Returns:
            Decorated function with rate limiting
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

    @rate_limit(2)  # 2 calls per second max
    def get_unread_emails(self, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        Enhanced version that retrieves more emails and formats them better for display
        """
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
                
                # Get the full message details
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
                        # Extract name and email address
                        if '<' in sender_full and '>' in sender_full:
                            sender_name = sender_full.split('<')[0].strip()
                            sender = sender_full.split('<')[1].split('>')[0].strip()
                        else:
                            sender = sender_full
                            sender_name = sender_full
                    elif header['name'] == 'Date':
                        date_str = header['value']
                
                # Get the message body
                body = self._get_message_body(msg)
                
                # Parse date into friendly format
                try:
                    date_obj = datetime.strptime(date_str.split('(')[0].strip(), "%a, %d %b %Y %H:%M:%S %z")
                    friendly_date = date_obj.strftime("%b %d, %Y at %I:%M %p")
                except Exception:
                    friendly_date = "Recently"
                
                # Create email object with additional fields
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
    
    def _get_message_body(self, message: Dict[str, Any]) -> str:
        """
        Extract the message body from the Gmail API response.
        
        Args:
            message: The message object from Gmail API
            
        Returns:
            The message body as text
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
    
    def get_all_labels(self) -> List[Dict[str, Any]]:
        """
        Get all available labels in the user's Gmail account.
        
        Returns:
            List of label objects with id and name
        """
        if not self.authorized or not self.service:
            print("Not authorized to access labels")
            return []
        
        try:
            # Get all labels
            results = self.service.users().labels().list(userId=self.user_id).execute()
            labels = results.get('labels', [])
            
            # Format the labels
            formatted_labels = []
            for label in labels:
                # Skip system labels like INBOX, SENT, etc.
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
        """
        Send an email.
        
        Args:
            to: Recipient email address
            subject: Email subject
            body: Email body content
            reply_to: Message ID to reply to (if applicable)
            
        Returns:
            True if email was sent successfully, False otherwise
        """
        if not self.authorized or not self.service:
            print("Not authorized to send email")
            return False
        
        try:
            # Create email message
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            
            # Add In-Reply-To header if replying to an email
            if reply_to:
                message['In-Reply-To'] = reply_to
                message['References'] = reply_to
            
            # Add the message body
            msg = MIMEText(body)
            message.attach(msg)
            
            # Encode the message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            # Send the message
            self.service.users().messages().send(
                userId=self.user_id,
                body={'raw': raw_message}
            ).execute()
            
            return True
        
        except HttpError as error:
            print(f"An error occurred: {error}")
            return False
    
    def apply_label(self, email_id: str, label: str) -> bool:
        """
        Apply a label to an email.
        
        Args:
            email_id: The ID of the email
            label: The label to apply
            
        Returns:
            True if label applied successfully, False otherwise
        """
        if not self.authorized or not self.service:
            print("Not authorized to apply labels")
            return False
        
        try:
            # First, check if the label exists
            label_id = self._get_or_create_label(label)
            
            if not label_id:
                return False
            
            # Apply the label to the email
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
        """
        Get the ID of a label, creating it if it doesn't exist.
        
        Args:
            label_name: The name of the label
            
        Returns:
            The label ID if successful, None otherwise
        """
        try:
            # Get all labels
            results = self.service.users().labels().list(userId=self.user_id).execute()
            labels = results.get('labels', [])
            
            # Check if the label already exists
            for label in labels:
                if label['name'].lower() == label_name.lower():
                    return label['id']
            
            # Create the label if it doesn't exist
            new_label = self.service.users().labels().create(
                userId=self.user_id,
                body={'name': label_name}
            ).execute()
            
            return new_label['id']
        
        except HttpError as error:
            print(f"An error occurred: {error}")
            return None
    
    def trash_email(self, email_id: str) -> bool:
        """
        Move an email to trash.
        
        Args:
            email_id: The ID of the email to trash
            
        Returns:
            True if successful, False otherwise
        """
        if not self.authorized or not self.service:
            print("Not authorized to trash emails")
            return False
            
        try:
            # Move to trash by adding TRASH label and removing INBOX label
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
        """
        Mark an email as read by removing the UNREAD label.
        
        Args:
            email_id: The ID of the email to mark as read
            
        Returns:
            True if successful, False otherwise
        """
        if not self.authorized or not self.service:
            print("Not authorized to modify emails")
            return False
            
        try:
            # Remove UNREAD label
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