import pyttsx3

# Initialize text-to-speech engine
engine = pyttsx3.init()
voices = engine.getProperty('voices')

# List available voices
print("Available voices:")
for index, voice in enumerate(voices):
    print(f"Index {index}: {voice.name} - {voice.languages}")

# Check the number of available voices and set the desired one
if len(voices) > 2:
    engine.setProperty('voice', voices[2].id)  # Use the voice at index 2
else:
    print("Not enough voices available. Using the default voice.")
    if voices:
        engine.setProperty('voice', voices[0].id)  # Fallback to the first available voice

# Continue with your text-to-speech logic...
