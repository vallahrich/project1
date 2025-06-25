from google.cloud import texttospeech
import pygame
import io

class TextToSpeech:
    def __init__(self):
        self.client = texttospeech.TextToSpeechClient()
        self.voice = texttospeech.VoiceSelectionParams(
            language_code="de-DE",  # Changed to German
            name="de-DE-Neural2-F",  # German female voice
            ssml_gender=texttospeech.SsmlVoiceGender.FEMALE
        )
        self.audio_config = texttospeech.AudioConfig(
            audio_encoding=texttospeech.AudioEncoding.LINEAR16,
            speaking_rate=1.0,
            pitch=0
        )
        # Initialize pygame mixer for audio playback
        pygame.mixer.init()

    def synthesize_speech(self, text):
        """Convert text to speech and return audio content"""
        synthesis_input = texttospeech.SynthesisInput(text=text)
        response = self.client.synthesize_speech(
            input=synthesis_input,
            voice=self.voice,
            audio_config=self.audio_config
        )
        return response.audio_content

    def play_audio(self, audio_content):
        """Play audio content using pygame"""
        # Create a BytesIO object from the audio content
        audio_file = io.BytesIO(audio_content)
        
        # Load and play the audio
        pygame.mixer.music.load(audio_file)
        pygame.mixer.music.play()
        
        # Wait for the audio to finish playing
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)

    def speak(self, text):
        """Convert text to speech and play it"""
        try:
            audio_content = self.synthesize_speech(text)
            self.play_audio(audio_content)
            return True
        except Exception as e:
            print(f"Fehler bei der Sprachsynthese: {str(e)}")  # German: Error during text-to-speech
            return False

if __name__ == "__main__":
    # Test the text-to-speech functionality
    tts = TextToSpeech()
    test_text = "Hallo! Ich bin Ihr Rasa-Sprachassistent. Wie kann ich Ihnen heute helfen?"  # German greeting
    tts.speak(test_text)