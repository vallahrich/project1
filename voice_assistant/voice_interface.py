import asyncio
import aiohttp
from speech_to_text import SpeechToText
from text_to_speech import TextToSpeech

class VoiceInterface:
    def __init__(self):
        self.stt = SpeechToText()
        self.tts = TextToSpeech()
        self.rasa_url = "http://localhost:5005/webhooks/rest/webhook"

    async def get_rasa_response(self, user_message):
        """Get response from Rasa via HTTP API"""
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.rasa_url,
                json={"sender": "user", "message": user_message}
            ) as response:
                return await response.json()

    async def process_voice_input(self):
        """Process voice input and get Rasa response"""
        # Convert speech to text
        user_input = self.stt.listen_and_transcribe(duration=30)
        print(f"Sie sagten: {user_input}")  # German: You said

        if not user_input.strip():
            self.tts.speak("Das habe ich nicht verstanden. Könnten Sie das bitte wiederholen?")  # German: I didn't catch that. Could you please repeat?
            return True

        # Get response from Rasa
        responses = await self.get_rasa_response(user_input)
        
        # Convert Rasa's response to speech
        for response in responses:
            if response.get("text"):
                print(f"Assistent: {response['text']}")  # German: Assistant
                self.tts.speak(response["text"])

        return True

    async def run(self):
        """Run the voice interface"""
        # Welcome message in German
        welcome_text = "Hallo! Ich bin Ihr Rasa-Sprachassistent. Wie kann ich Ihnen heute helfen?"
        print("Assistent:", welcome_text)  # German: Assistant
        self.tts.speak(welcome_text)

        while True:
            try:
                should_continue = await self.process_voice_input()
                if not should_continue:
                    break
            except Exception as e:
                print(f"Fehler: {str(e)}")  # German: Error
                break

if __name__ == "__main__":
    # Create and run the voice interface
    voice_interface = VoiceInterface()
    asyncio.run(voice_interface.run())