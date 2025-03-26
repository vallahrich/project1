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
    
    # Keep the same connect() method as the original
    def connect(self):
        """Same connect method as original EmailClient"""
        # Implementation remains the same as the original EmailClient
        # [Omitted for brevity]
        pass

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
                except:
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

    def _get_message_body(self, message):
        """Same implementation as the original"""
        # [Implementation remains the same as the original EmailClient]
        pass
    
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
    
    # Include the send_email, apply_label, and other required methods from the original
    # [Implementation of other methods from the original EmailClient]