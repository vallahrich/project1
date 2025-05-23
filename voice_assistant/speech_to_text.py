from google.cloud.speech import SpeechClient
from google.cloud.speech import RecognitionConfig, RecognitionAudio
import pyaudio
import wave
import io

class SpeechToText:
    def __init__(self):
        self.client = SpeechClient()
        self.audio_config = RecognitionConfig(
            encoding=RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code="en-US",
            model="default"
        )

    def record_audio(self, seconds=30, filename="input.wav"):
        """Record audio from microphone"""
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000

        p = pyaudio.PyAudio()
        stream = p.open(format=FORMAT,
                       channels=CHANNELS,
                       rate=RATE,
                       input=True,
                       frames_per_buffer=CHUNK)

        print("* Recording audio...")
        frames = []

        for i in range(0, int(RATE / CHUNK * seconds)):
            data = stream.read(CHUNK)
            frames.append(data)

        print("* Done recording")

        stream.stop_stream()
        stream.close()
        p.terminate()

        # Save the recorded data as a WAV file
        wf = wave.open(filename, 'wb')
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        wf.writeframes(b''.join(frames))
        wf.close()

        return filename

    def transcribe_audio(self, audio_file):
        """Transcribe audio file to text"""
        with io.open(audio_file, "rb") as audio_file:
            content = audio_file.read()

        audio = RecognitionAudio(content=content)
        response = self.client.recognize(
            config=self.audio_config,
            audio=audio
        )

        transcriptions = []
        for result in response.results:
            transcriptions.append(result.alternatives[0].transcript)

        return " ".join(transcriptions)

    def listen_and_transcribe(self, duration=30):
        """Record audio and transcribe it to text"""
        audio_file = self.record_audio(seconds=duration)
        return self.transcribe_audio(audio_file)

if __name__ == "__main__":
    # Test the speech-to-text functionality
    stt = SpeechToText()
    try:
        text = stt.listen_and_transcribe(duration=30)
        print(f"Transcribed text: {text}")
    except Exception as e:
        print(f"Error during speech-to-text: {str(e)}") 