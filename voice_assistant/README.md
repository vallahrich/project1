# Voice Interface for Rasa Assistant

This component adds voice capabilities to the Rasa assistant using Google's Speech-to-Text and Text-to-Speech APIs.

## Prerequisites

1. Google Cloud Platform Account
2. Google Cloud Project with Speech-to-Text and Text-to-Speech APIs enabled
3. Service account credentials with access to these APIs
4. Python 3.8 or higher
5. Running Rasa server with trained model

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Set up Google Cloud credentials:
```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/your/service-account-key.json"
```

3. Make sure your Rasa server is running:
```bash
# Terminal 1: Run Rasa server
rasa run --enable-api

# Terminal 2: Run Rasa actions
rasa run actions
```

## Usage

1. Start the voice assistant:
```bash
python voice_assistant.py
```

2. Speak to the assistant in either English or German
3. The assistant will:
   - Convert your speech to text
   - Process it through Rasa
   - Convert Rasa's response to speech
   - Play the response

## Features

- Real-time speech recognition
- Automatic language detection (English/German)
- Natural-sounding responses
- Seamless integration with Rasa
- Support for all Rasa functionalities:
  - Email management
  - Emergency assistance
  - Medication reminders
  - General conversation

## Language Support

- English (en-US)
- German (de-DE)

## Troubleshooting

1. If you get audio device errors:
   - Check if your microphone is properly connected
   - Verify microphone permissions
   - Try a different audio input device

2. If speech recognition is not working:
   - Verify your Google Cloud credentials
   - Check your internet connection
   - Ensure the Speech-to-Text API is enabled

3. If Rasa integration fails:
   - Verify Rasa server is running
   - Check if the model is properly loaded
   - Ensure action server is running 