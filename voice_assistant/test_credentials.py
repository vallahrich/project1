from google.cloud import speech_v1
from google.cloud import texttospeech_v1

def test_credentials():
    print("Google Cloud-Anmeldedaten werden getestet...")  # German: Testing Google Cloud credentials
    
    try:
        # Test Speech-to-Text client
        speech_client = speech_v1.SpeechClient()
        print("✓ Speech-to-Text-Client erfolgreich initialisiert")  # German: Successfully initialized
        
        # Test Text-to-Speech client
        tts_client = texttospeech_v1.TextToSpeechClient()
        print("✓ Text-to-Speech-Client erfolgreich initialisiert")  # German: Successfully initialized
        
        # Try a simple TTS request with German
        synthesis_input = texttospeech_v1.SynthesisInput(text="Test erfolgreich")  # German: Test successful
        voice = texttospeech_v1.VoiceSelectionParams(
            language_code="de-DE",  # Changed to German
            name="de-DE-Neural2-F",  # German voice
            ssml_gender=texttospeech_v1.SsmlVoiceGender.FEMALE
        )
        audio_config = texttospeech_v1.AudioConfig(
            audio_encoding=texttospeech_v1.AudioEncoding.LINEAR16
        )
        
        response = tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )
        print("✓ Text-to-Speech-API-Aufruf erfolgreich durchgeführt")  # German: Successfully made API call
        
        print("\nAlle Tests bestanden! Ihre Anmeldedaten funktionieren korrekt.")  # German: All tests passed
        
    except Exception as e:
        print("\n❌ Fehler beim Testen der Anmeldedaten:")  # German: Error testing credentials
        print(e)
        print("\nBitte überprüfen Sie, dass:")  # German: Please verify that
        print("1. Ihre Anmeldedatei sich am korrekten Ort befindet")  # German: credentials file is in correct location
        print("2. Die GOOGLE_APPLICATION_CREDENTIALS-Umgebungsvariable korrekt gesetzt ist")  # German: env variable is set correctly
        print("3. Die APIs in Ihrer Google Cloud Console aktiviert sind")  # German: APIs are enabled in console

if __name__ == "__main__":
    test_credentials()