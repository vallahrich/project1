from google.cloud import speech_v1
from google.cloud import texttospeech_v1

def test_credentials():
    print("Testing Google Cloud credentials...")
    
    try:
        # Test Speech-to-Text client
        speech_client = speech_v1.SpeechClient()
        print("✓ Speech-to-Text client initialized successfully")
        
        # Test Text-to-Speech client
        tts_client = texttospeech_v1.TextToSpeechClient()
        print("✓ Text-to-Speech client initialized successfully")
        
        # Try a simple TTS request
        synthesis_input = texttospeech_v1.SynthesisInput(text="Test successful")
        voice = texttospeech_v1.VoiceSelectionParams(
            language_code="en-US",
            ssml_gender=texttospeech_v1.SsmlVoiceGender.NEUTRAL
        )
        audio_config = texttospeech_v1.AudioConfig(
            audio_encoding=texttospeech_v1.AudioEncoding.LINEAR16
        )
        
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        print("✓ Successfully made a Text-to-Speech API call")
        
        print("\nAll tests passed! Your credentials are working correctly.")
        
    except Exception as e:
        print("\n❌ Error testing credentials:")
        print(e)
        print("\nPlease verify that:")
        print("1. Your credentials file is in the correct location")
        print("2. The GOOGLE_APPLICATION_CREDENTIALS environment variable is set correctly")
        print("3. The APIs are enabled in your Google Cloud Console")

if __name__ == "__main__":
    test_credentials() 