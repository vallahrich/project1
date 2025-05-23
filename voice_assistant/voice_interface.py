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
        print(f"You said: {user_input}")

        if not user_input.strip():
            self.tts.speak("I didn't catch that. Could you please repeat?")
            return True

        # Get response from Rasa
        responses = await self.get_rasa_response(user_input)
        
        # Convert Rasa's response to speech
        for response in responses:
            if response.get("text"):
                print(f"Assistant: {response['text']}")
                self.tts.speak(response["text"])

        return True

    async def run(self):
        """Run the voice interface"""
        # Welcome message
        welcome_text = "Hello! I'm your Rasa voice assistant. How can I help you today?"
        print("Assistant:", welcome_text)
        self.tts.speak(welcome_text)

        while True:
            try:
                should_continue = await self.process_voice_input()
                if not should_continue:
                    break
            except Exception as e:
                print(f"Error: {str(e)}")
                break

if __name__ == "__main__":
    # Create and run the voice interface
    voice_interface = VoiceInterface()
    asyncio.run(voice_interface.run())