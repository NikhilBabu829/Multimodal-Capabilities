import queue
import wave
from datetime import datetime
from pathlib import Path

import sounddevice as sd
from rich import print
from rich import console
from rich.prompt import Prompt

from faster_whisper import WhisperModel

import httpx
import os
from dotenv import load_dotenv

model_size = "base"
load_dotenv()
model = WhisperModel(model_size, device="cpu", compute_type="int8")

con = console.Console()

# Speech-to-text engines want 16kHz mono PCM. Recording anything else just
# means they resample it before doing the real work.
SAMPLE_RATE = 16000
CHANNELS = 1
SAMPLE_WIDTH = 2  # bytes per sample, int16
RECORDINGS_DIR = Path(__file__).parent / "recordings"


def list_input_devices():
    con.print("\n[bold]Available input devices:[/bold]")
    default_input = sd.default.device[0]
    for index, device in enumerate(sd.query_devices()):
        if device["max_input_channels"] < 1:
            continue
        marker = " [green](default)[/green]" if index == default_input else ""
        con.print(f"  {index}: {device['name']}{marker}")
    print("")


def record_to_wav(file_path: Path):
    audio_chunks = queue.Queue()

    def callback(indata, frames, time_info, status):
        # Runs on PortAudio's thread. Keep it to a copy and a put, nothing
        # slow, or the input buffer overflows and audio drops out.
        if status:
            con.log(f"Input stream status: {status}")
        audio_chunks.put(bytes(indata))

    con.print("[bold red]Recording...[/bold red] press Enter to stop")
    with sd.RawInputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="int16",
        callback=callback,
    ):
        input()

    recorded_bytes = b""
    while not audio_chunks.empty():
        recorded_bytes += audio_chunks.get()

    # Measure from the audio itself rather than the wall clock, so opening the
    # device doesn't get counted as recorded time.
    duration = len(recorded_bytes) / (SAMPLE_RATE * SAMPLE_WIDTH * CHANNELS)

    if not recorded_bytes:
        con.print("[bold red]Nothing was recorded.[/bold red] Check microphone permissions.")
        return None

    file_path.parent.mkdir(exist_ok=True)
    with wave.open(str(file_path), "wb") as wav_file:
        wav_file.setnchannels(CHANNELS)
        wav_file.setsampwidth(SAMPLE_WIDTH)
        wav_file.setframerate(SAMPLE_RATE)
        wav_file.writeframes(recorded_bytes)

    con.print(f"Saved [bold]{file_path}[/bold] ({duration:.1f}s, {SAMPLE_RATE}Hz mono)")
    return file_path

def sendingToAPI(formatted_data, transcription_language):
    api_key = os.getenv("API_KEY")
    try:
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        payload = {
            "model": "claude-haiku-4-5-20251001",
            "max_tokens": 1000,
            "messages": [
                {
                    "role" : "user", "content" : [{text} for text in formatted_data]
                },
                {
                    "type" : "text", "text" : "What is the audio file about?"
                }
            ]
        }
        print(payload)
        with httpx.Client() as client:
            api_response = client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            respones_json = api_response.json()
            print(respones_json)
    except Exception as er:
        print(er)

def transcribe(wav_path: Path):
    # TODO: this is yours to build.
    segments, info = model.transcribe(wav_path, beam_size=5)
    formating_data = []
    for segment in segments:
        formating_data.append(segment.text)
    transcription_language = info.language
    sendingToAPI(formating_data, transcription_language)

def main():
    con.log("Starting the recorder")
    print("This application records your voice and saves it as a .wav file.")
    print("Press Enter to start recording, type 'devices' to list microphones, or 'q' to quit.")
    while True:
        try:
            command = Prompt.ask("").strip().lower()
            if command in ("q", "quit", "exit"):
                con.print("Exiting the program. Goodbye!", style="bold red")
                break
            if command == "devices":
                list_input_devices()
                continue
            if command not in ("", "r", "record"):
                con.print("Unknown command. Use Enter, 'devices', or 'q'.")
                continue

            file_name = datetime.now().strftime("%Y-%m-%d_%H%M%S") + ".wav"
            saved_path = record_to_wav(RECORDINGS_DIR / file_name)
            if saved_path is None:
                continue

            try:
                transcript = transcribe(saved_path)
                con.print(f"Transcript: {transcript}")
            except NotImplementedError:
                con.print("Transcription is not wired up yet - implement transcribe() in record.py")
        except KeyboardInterrupt:
            con.print("\nExiting the program. Goodbye!", style="bold red")
            break
        except EOFError:
            con.print("\nExiting the program. Goodbye!", style="bold red")
            break


if __name__ == "__main__":
    main()
