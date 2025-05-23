import os
import queue
import threading
import time
from google.cloud import speech_v1
from google.cloud import texttospeech_v1
import pyaudio
import wave
from rasa.core.agent import Agent
from rasa.utils.endpoints import EndpointConfig
import asyncio

class VoiceAssistant:
    def __init__(self):
        # Audio recording parameters
        self.CHUNK = 1024
        self.FORMAT = pyaudio.paInt16
        self.CHANNELS = 1
        self.RATE = 16000
        self.STREAMING_LIMIT = 240000  # 4 minutes
        self.SAMPLE_WIDTH = 2

        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()

        # Initialize Google Cloud clients
        self.speech_client = speech_v1.SpeechClient()
        self.tts_client = texttospeech_v1.TextToSpeechClient()

        # Initialize Rasa agent
        self.action_endpoint = EndpointConfig(url="http://localhost:5055/webhook")
        self.agent = None
        self.load_agent()

        # Create a thread-safe queue for audio data
        self.audio_queue = queue.Queue()
        self.is_listening = False

    async def load_agent(self):
        """Load the Rasa agent with the trained model"""
        self.agent = await Agent.load(
            model_path="models",
            action_endpoint=self.action_endpoint
        )

    def start_listening(self):
        """Start listening to audio input"""
        self.is_listening = True
        stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            input=True,
            frames_per_buffer=self.CHUNK
        )

        print("Listening... Speak now!")

        while self.is_listening:
            data = stream.read(self.CHUNK, exception_on_overflow=False)
            self.audio_queue.put(data)

        stream.stop_stream()
        stream.close()

    def stop_listening(self):
        """Stop listening to audio input"""
        self.is_listening = False

    def transcribe_audio(self):
        """Transcribe audio using Google Speech-to-Text"""
        config = speech_v1.RecognitionConfig(
            encoding=speech_v1.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=self.RATE,
            language_code="en-US",  # Default to English
            alternative_language_codes=["de-DE"]  # Add German as alternative
        )

        streaming_config = speech_v1.StreamingRecognitionConfig(
            config=config,
            interim_results=True
        )

        def generate_requests():
            while self.is_listening:
                try:
                    data = self.audio_queue.get(timeout=1)
                    yield speech_v1.StreamingRecognizeRequest(audio_content=data)
                except queue.Empty:
                    continue

        responses = self.speech_client.streaming_recognize(
            config=streaming_config,
            requests=generate_requests()
        )

        for response in responses:
            if not response.results:
                continue

            result = response.results[0]
            if result.is_final:
                return result.alternatives[0].transcript

    async def process_with_rasa(self, text_input):
        """Process text input with Rasa and get response"""
        if not self.agent:
            await self.load_agent()
        
        response = await self.agent.handle_text(text_input)
        return response[0]["text"] if response else "I'm sorry, I didn't understand that."

    def text_to_speech(self, text, language_code="en-US"):
        """Convert text to speech using Google Text-to-Speech"""
        synthesis_input = texttospeech_v1.SynthesisInput(text=text)

        voice = texttospeech_v1.VoiceSelectionParams(
            language_code=language_code,
            ssml_gender=texttospeech_v1.SsmlVoiceGender.NEUTRAL
        )

        audio_config = texttospeech_v1.AudioConfig(
            audio_encoding=texttospeech_v1.AudioEncoding.LINEAR16
        )

        response = self.tts_client.synthesize_speech(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config
        )

        # Play the audio response
        stream = self.audio.open(
            format=self.FORMAT,
            channels=self.CHANNELS,
            rate=self.RATE,
            output=True
        )
        stream.write(response.audio_content)
        stream.stop_stream()
        stream.close()

    async def run(self):
        """Main loop for the voice assistant"""
        try:
            # Start listening in a separate thread
            listen_thread = threading.Thread(target=self.start_listening)
            listen_thread.start()

            while True:
                # Get transcription
                transcript = self.transcribe_audio()
                if transcript:
                    print(f"You said: {transcript}")

                    # Process with Rasa
                    response = await self.process_with_rasa(transcript)
                    print(f"Assistant: {response}")

                    # Convert response to speech
                    # Detect language (simplified - you might want to use a language detection library)
                    language_code = "de-DE" if any(word in transcript.lower() for word in ["hilfe", "danke", "bitte"]) else "en-US"
                    self.text_to_speech(response, language_code)

                time.sleep(0.1)  # Small delay to prevent CPU overuse

        except KeyboardInterrupt:
            print("\nStopping voice assistant...")
            self.stop_listening()
            listen_thread.join()
            self.audio.terminate()

if __name__ == "__main__":
    assistant = VoiceAssistant()
    asyncio.run(assistant.run()) 