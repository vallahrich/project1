# Email Assistant Chatbot

This is an AI-powered email assistant built with Rasa Pro that helps users manage their emails through a conversational interface.

## Features

- Check for new emails
- Read email content
- Draft and send replies
- Sort emails into categories
- Label emails
- Uses Gmail API for email operations
- Uses LLM models for natural language understanding

## Prerequisites

- Python 3.8+ 
- Rasa Pro license
- Gmail API credentials
- OpenAI API key

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/email-assistant.git
cd email-assistant
```

2. Create a virtual environment and activate it:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install rasa-pro
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

## Setting Up Gmail API

1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project
3. Enable the Gmail API for your project
4. Create OAuth 2.0 credentials (Desktop application)
5. Download the credentials JSON file
6. Place the credentials file in `credentials/gmail_credentials.json` in your project directory

## Configuration

Set the following environment variables:

```bash
# Optional - if not set, the app will look for credentials in the credentials/ directory
export GMAIL_CREDENTIALS_PATH=/path/to/your/credentials.json
export GMAIL_TOKEN_PATH=/path/to/save/token.json

# Required for LLM integration
export OPENAI_API_KEY=your_openai_api_key
```

## Directory Structure

```
email_assistant/
├── actions/                   # Custom actions
│   ├── __init__.py           # Action registration
│   ├── email_client.py       # Gmail API client
│   ├── email_check_actions.py # Actions for checking emails
│   ├── email_reply_actions.py # Actions for replying to emails
│   └── email_organize_actions.py # Actions for organizing emails
├── credentials/              # Store API credentials here
│   ├── gmail_credentials.json # Gmail API credentials
│   └── gmail_token.json      # Generated OAuth token
├── data/                     # Training data
│   └── email.yml             # Email flow definitions
├── config.yml                # Rasa configuration
├── credentials.yml           # Channel credentials
├── domain.yml                # Domain definition
├── endpoints.yml             # Endpoint configuration
└── README.md                 # This file
```

## Running the Bot

1. Start the action server:
```bash
rasa run actions
```

2. Start the Rasa server:
```bash
rasa run --enable-api --endpoints endpoints.yml
```

3. Train the model (if needed):
```bash
rasa train
```

## Features and Capabilities

The email assistant can:

- Check for new emails in your inbox
- Read the content of emails
- Draft professional replies using AI
- Send replies to emails
- Organize emails by content into categories
- Apply labels to emails

## First-time Usage

The first time you run the bot, it will:

1. Try to authenticate with the Gmail API
2. If no valid token exists, it will open a browser window for you to authorize the application
3. After authorization, it will save the token for future use

## Troubleshooting

- **Authentication Issues**: Delete the token.json file and restart to go through the authentication flow again.
- **Missing Credentials**: Ensure your credentials.json file is properly placed and has the correct format.
- **LLM Integration Issues**: Check that your OpenAI API key is correctly set in the environment.

## License

This project is licensed under the MIT License - see the LICENSE file for details.