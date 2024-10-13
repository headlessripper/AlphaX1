import ctypes
import datetime
import json
import logging
import os
import platform  # Ensure you only import platform here
import queue
import random
import re
import sqlite3
import subprocess
import sys
import threading
import time
import webbrowser
from urllib.parse import quote

import customtkinter
import numpy as np
import pyttsx3
import requests
import spacy
import speech_recognition as sr
import spotipy
import torch
import wikipedia
import wolframalpha
from bs4 import BeautifulSoup
from pydub import AudioSegment
from pydub.playback import play
from spotipy.oauth2 import SpotifyOAuth
from transformers import GPT2LMHeadModel, GPT2Tokenizer
from youtubesearchpython import VideosSearch

# Assume `speak` function is defined elsewhere
from Assistant import speak as external_speak
from nlu import ExtendedNLU
from pydub import AudioSegment
from pydub.playback import play
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)


customtkinter.set_appearance_mode("dark blue")

# Initialize text-to-speech engine
engine = pyttsx3.init()
voices = engine.getProperty('voices')

# Check the number of available voices
if len(voices) > 1:
    engine.setProperty('voice', voices[1].id)  # Use the voice at index 2
else:
    print("Not enough voices available. Using the default voice.")
    # Optionally, you can set a default voice
    if voices:
        engine.setProperty('voice', voices[0].id)  # Fallback to the first available voice


# Initialize GPT-2 model and tokenizer
model_name = 'gpt2'
tokenizer = GPT2Tokenizer.from_pretrained(model_name)
model = GPT2LMHeadModel.from_pretrained(model_name)

# Set up model parameters
max_length = 100
device = 'cuda' if torch.cuda.is_available() else 'cpu'  # Use GPU if available
model.to(device)  # Move the model to the appropriate device

# Initialize Wolfram Alpha API
wolfram_alpha_app_id = 'GWPPPU-TU3HQER89G'  # Replace it with your actual app ID
wolfram_alpha_client = wolframalpha.Client(wolfram_alpha_app_id)

# Load English tokenizer, tagger, parser, NER and word vectors
nlp = spacy.load("en_core_web_sm")

# Speech recognition setup
recognizer = sr.Recognizer()
microphone = sr.Microphone()

# Initialize SQLite connections
short_term_conn = sqlite3.connect('short_term_memory.sqlite')
long_term_conn = sqlite3.connect('long_term_memory.sqlite')

logging.basicConfig(level=logging.INFO, format='%(pastime)s - %(levelness)s - %(message)s')

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id="53bea1185b2541aca8636f8e97799542",
                                               client_secret="e27ddc7a45dd49d0a969f3c5c91b0029",
                                               redirect_uri="https://open.spotify.com/",
                                               scope="user-read-playback-state,user-modify-playback-state"))


class Brain:
    def __init__(self, intelligence):

        self.sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id='53bea1185b2541aca8636f8e97799542',
                                                            client_secret='"e27ddc7a45dd49d0a969f3c5c91b0029',
                                                            redirect_uri='https://open.spotify.com',
                                                            scope='user-read-playback-state,user-modify-playback-state'))

        logging.basicConfig(filename='assistant_log.txt', level=logging.INFO, format='%(pastime)s - %(message)s')
        self.intelligence = intelligence
        self.ready_queue = queue.PriorityQueue()  # Priority queue for processes ready to execute
        self.mutex = threading.Lock()  # Mutex for shared resources or critical sections
        self.suspended = False
        self.active = False  # Flag to indicate if the assistant is suspended
        self.alarm_sound_file = "Alarm music\Alarm.mp3"  # Default audio file path
        self.alarm_set = False
        self.alarm_time_12 = None
        self.alarm_time_24 = None
        self.listening = True
        self.processing = False
        self.nlu = ExtendedNLU("AIzaSyBwehvm4IIKA_FZeeJL3ddFUtiIxtgWtUA", "372292dbe9b8f4339")  # Initialize NLU with API key and ID
        self.alarm_triggered = threading.Event()
        self.processed_commands = set()  # Set to track processed commands


        # Set up logging
        self.memories = []
        self.reminder_interval = 3 * 60 * 60  # 3 hours in seconds
        self.deletion_interval = 24 * 60 * 60  # 24 hours in seconds
        self.sleep_event = threading.Event()  # Event for controlling sleep
        self.is_sleeping = False
        self.listening_thread = threading.Thread(target=self.listen_for_wake_word, daemon=True)

        # Initialize SQLite connections and cursors
        self.short_term_conn = short_term_conn
        self.long_term_conn = long_term_conn
        self.short_term_cursor = self.short_term_conn.cursor()
        self.long_term_cursor = self.long_term_conn.cursor()

        self.log_file = open("assistant_log.txt", "a")
        self.start_background_tasks()

        # Create tables if they don't exist
        self.setup_tables()

    def setup_tables(self):
        # Create tables if they don't exist
        self.short_term_cursor.execute('''
            CREATE TABLE IF NOT EXISTS short_term_memory (
                timestamp INTEGER PRIMARY KEY,
                memory_data TEXT
            )
        ''')
        self.long_term_cursor.execute('''
            CREATE TABLE IF NOT EXISTS long_term_memory (
                key TEXT PRIMARY KEY,
                memory_data TEXT
            )
        ''')
        self.short_term_conn.commit()
        self.long_term_conn.commit()

    def perceive(self, sensory_data):
        # Placeholder for handling sensory data asynchronously
        threads = []

        # Example: Threading for speech recognition
        if 'speech' in sensory_data:
            speech_thread = threading.Thread(target=self.process_speech, args=(sensory_data['speech'],))
            threads.append(speech_thread)
            speech_thread.start()

        # Example: Threading for API response handling
        if 'api_response' in sensory_data:
            api_thread = threading.Thread(target=self.process_api_response, args=(sensory_data['api_response'],))
            threads.append(api_thread)
            api_thread.start()

        # Example: Threading for system events
        if 'system_event' in sensory_data:
            system_event_thread = threading.Thread(target=self.process_system_event,
                                                   args=(sensory_data['system_event'],))
            threads.append(system_event_thread)
            system_event_thread.start()

        # Example: Threading for sensor integration
        if 'sensor_data' in sensory_data:
            sensor_thread = threading.Thread(target=self.process_sensor_data, args=(sensory_data['sensor_data'],))
            threads.append(sensor_thread)
            sensor_thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        return "Perception completed."

    def processing(self, data):
        # Placeholder for additional processing steps
        # For now, directly run SJN scheduling algorithm with example tasks
        tasks = [
            (1, 5),
            (2, 3),
            (3, 7),
            (4, 2),
            (5, 4)
        ]
        self.run_sjn(tasks)

    def run_sjn(self, tasks):
        # SJN scheduling algorithm for CPU-bound and I/O-bound tasks
        for task_id, burst_time in tasks:
            self.ready_queue.put((burst_time, task_id))

        while not self.ready_queue.empty():
            self.mutex.acquire()
            burst_time, task_id = self.ready_queue.get()
            self.mutex.release()

            # Simulate CPU-bound task
            decision = self.make_decision(task_id)
            self.execute_action(decision)

            # Simulate I/O-bound task
            io_time = random.randint(1, 3)  # Simulate random I/O wait time
            self.io_bound_task(task_id, io_time)

            # Transfer to long-term memory and update intelligence
            self.transfer_to_long_term_memory(self.short_term_memory[-1])
            self.update_intelligence(decision)

            # Provide feedback on completion
            completion_time = random.uniform(30, 180)  # Simulate completion time
            self.feedback(task_id, completion_time)

            # Notify system or trigger actions on task completion
            self.task_completed_notification(task_id)

            self.log_file = open("assistant_log.txt", "a")

    def make_decision(self, task_id):
        # Decision-making algorithm dependent on intelligence and task_id
        if self.intelligence > 0.5:
            options = ['option1', 'option2', 'option3']
        else:
            options = ['option4', 'option5', 'option6']
        decision = random.choice(options)
        print(f"Task {task_id}: Made decision {decision}")
        return decision

    def execute_action(self, decision):
        # Action execution dependent on decision and processing
        processed_decision = self.processing(decision)
        print(f"Task {decision}: Executing action: {processed_decision}")
        time.sleep(1)  # Simulate action time

    @staticmethod
    def io_bound_task(task_id, io_time):
        print(f"Task {task_id}: Executing I/O-bound task, waiting for {io_time} seconds.")
        time.sleep(io_time)
        print(f"Task {task_id}: I/O-bound task completed.")

    def transfer_to_long_term_memory(self, recent_memory):
        # Simulate the transfer of important information to long-term memory
        key = str(time.time())  # Use timestamp as the key
        self.store_long_term_memory(key, recent_memory)
        print("Information transferred to long-term memory.")

    def update_intelligence(self, decision):
        # Placeholder for updating intelligence based on decision
        # Example: Increase intelligence if the decision is successful
        if decision.startswith('option'):
            self.intelligence += 0.1
        else:
            self.intelligence -= 0.1
        print(f"Intelligence updated to {self.intelligence}")

    @staticmethod
    def feedback(task_id, completion_time):
        # Function to give feedback on tasks completed.
        if completion_time < 60:
            time_feedback = f"Great job! You completed Task '{task_id}' quickly."
        elif completion_time < 180:
            time_feedback = f"Well done! Task '{task_id}' took some time but you did it."
        else:
            time_feedback = f"It took a while, but Task '{task_id}' is completed."

        print("Feedback:")
        print("-" * 30)
        print(f"Task: {task_id}")
        print(f"Completion Time: {completion_time:.2f} seconds")
        print(f"Feedback: {time_feedback}")
        print("-" * 30)

    @staticmethod
    def task_completed_notification(task_id):
        # Placeholder for task completion notification to the system
        print(f"Task '{task_id}' has been completed. Notifying the system...")

    def start_background_tasks(self):
        """Start background threads for reminders and automatic deletion."""
        threading.Thread(target=self.reminder_loop, daemon=True).start()
        threading.Thread(target=self.deletion_loop, daemon=True).start()

    def reminder_loop(self):
        """Periodically remind users of their stored memories."""
        while True:
            time.sleep(self.reminder_interval)
            if not self.suspended:
                self.remind_users()

    def deletion_loop(self):
        """Automatically delete all stored memories every 24 hours."""
        while True:
            time.sleep(self.deletion_interval)
            self.clear_memories()

    def recognize_speech(self):
        last_text = ""
        command_executed = False  # Flag to track if a command was executed

        with microphone as source:
            recognizer.adjust_for_ambient_noise(source)
            print("Listening...")
            external_speak("I Am Listening")

            while self.listening:
                try:
                    # Listen indefinitely for speech with a timeout of 5 seconds
                    audio = recognizer.listen(source, timeout=None)

                    # Check if the audio contains speech
                    if self.is_speech(audio):
                        print("Speech detected. Starting recognition...")
                        self.processing = True

                        try:
                            print("Recognizing...")
                            text = recognizer.recognize_google(audio)
                            print(f"User said: {text}")

                            # Check if the command is the same as the last one
                            if text.lower() != last_text:
                                last_text = text.lower()  # Update the last command
                                command_executed = True  # Set the flag to True

                                if 'suspend' in text.lower():
                                    self.suspend_assistant()
                                elif 'unsuspend' in text.lower():
                                    self.unsuspend_assistant()
                                elif 'remember' in text.lower():
                                    self.remember_this(text)
                                elif 'set alarm to' in text.lower():
                                    self.set_alarm(text)
                                elif 'play' in text.lower():
                                    self.handle_music_command(text)
                                elif 'increase volume' in text.lower():
                                    self.change_volume('increase')
                                elif 'decrease volume' in text.lower():
                                    self.change_volume('decrease')
                                elif 'mute' in text.lower():
                                    self.change_volume('mute')
                                elif 'undo' in text.lower():
                                    self.change_volume('undo')
                                elif 'increase brightness' in text.lower():
                                    self.change_brightness('increase')
                                elif 'decrease brightness' in text.lower():
                                    self.change_brightness('decrease')
                                elif 'turn on Wi-Fi' in text.lower():
                                    self.control_wifi('turn on')
                                elif 'turn off Wi-Fi' in text.lower():
                                    self.control_wifi('turn off')
                                elif 'turn on Bluetooth' in text.lower():
                                    self.control_bluetooth('turn on')
                                elif 'turn off Bluetooth' in text.lower():
                                    self.control_bluetooth('turn off')
                                return text
                            # Reset command execution flags after processing
                            if command_executed:
                                command_executed = False
                                time.sleep(1)  # Small delay to avoid immediate reprocessing

                        except sr.UnknownValueError:
                            print("Google Speech Recognition could not understand audio")
                        except sr.RequestError as e:
                            print(f"Could not request results from Google Speech Recognition service; {e}")
                        self.processing = False
                    else:
                        print("Ignored non-speech audio")

                except sr.WaitTimeoutError:
                    # Continue listening if timeout occurs
                    continue

            return None

    @staticmethod
    def is_speech(audio, threshold=0.000001):
        # Get raw data from audio
        audio_data = np.frombuffer(audio.get_raw_data(), np.int16)

        # Normalize audio data to range [0, 1]
        audio_data = np.abs(audio_data) / 32768.0

        # Calculate the average energy of the audio data
        energy = np.mean(audio_data ** 2)

        # Consider it as speech if the energy exceeds the threshold
        return energy > threshold
    
    def handle_fallback(self, text):
        try:
            response = self.nlu.get_response(text)
            print("Alpha:", response)  # Optional: print response

            #external_speak(response)  # Optional: use text-to-speech to respond

            if "Would you like to open this link? (yes/no)" in response:
                external_speak("Please say yes or no.")
                user_response = self.get_user_input(self.recognizer, self.microphone)  # Get user response through speech
                if user_response.lower() == "yes":
                    link = self.extract_link(response)
                    if link:
                        self.open_link(link)
        except Exception as e:
            print(f"Error in fallback handling: {e}")

    def get_user_input(self, recognizer, source):
        # Listen for user input through speech
        try:
            audio = recognizer.listen(source, timeout=5)
            user_response = recognizer.recognize_google(audio)
            print(f"User response: {user_response}")
            return user_response
        except sr.UnknownValueError:
            print("Google Speech Recognition could not understand the response")
            return ""
        except sr.RequestError as e:
            print(f"Could not request results from Google Speech Recognition service; {e}")
            return ""

    def extract_link(self, response):
        # Implement a method to extract the link from the response
        import re
        match = re.search(r"Link: (\S+)", response)
        return match.group(1) if match else None

    def open_link(self, link):
        import webbrowser
        webbrowser.open(link)

    def main(self):
        while True:
            # Read input from stdin
            input_text = sys.stdin.readline().strip()
            if input_text:
                response = self.recognize_speech()
                # Write the response to stdout
                sys.stdout.write(response + "\n")
                sys.stdout.flush()
                # Use the speak function to provide a verbal response
                external_speak(response)

    @staticmethod
    def process_speech(speech_data):
        # Placeholder for processing speech data asynchronously
        print(f"Processing speech data: {speech_data}")

    @staticmethod
    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    def process_speech_command(self, command):
        # Process speech command from user
        print(f"Processing speech command: {command}")

        # Example: Calculate mathematical expression
        if "calculate" in command:
            self.calculate(command)

        # Example: Open a website
        elif "website" in command:
            self.open_website(command)

        elif "hello" in command:
            response = self.greet_and_respond(command)  # Pass the whole command to greet_and_respond
            external_speak(response)

        # Example: Search the web
        elif "search for" in command:
            self.search_web(command)

        # Example: Provide information
        elif "tell me about" in command:
            self.tell_about(command)

        # Example: Suspend assistant
        elif "suspend" in command:
            self.suspend_assistant()

        # Example: Unsuspend assistant
        elif "unsuspend" in command:
            self.unsuspend_assistant()

        # Example: Shutdown assistant
        elif "shutdown my computer" in command:
            self.shutdown()

        # Example: Say goodbye
        elif "goodbye" in command:
            self.Good_bye()

        # Example: Put assistant to sleep
        elif "put my computer to sleep" in command:
            self.sleep()

        # Example: Get current time
        elif "time" in command:
            self.get_time()

        # Example: Get current date
        elif "date" in command:
            self.get_date()

        elif "News" in command:
            self.fetch_and_display_news()

        # Handle command "alpha hibernate for [duration]"
        elif "hibernate" in command:
            try:
                # Define a regular expression pattern to match durations like "for 5 minutes" or "for 10 seconds"
                duration_pattern = r'for (\d+) (seconds?|minutes?)'

                # Use regular expression to find duration in the command
                match = re.search(duration_pattern, command)

                if match:
                    duration_value = int(match.group(1))  # Extract the numeric value of duration
                    unit = match.group(2)  # Extract the unit of duration (seconds or minutes)

                    # Convert duration to seconds based on the unit
                    if unit.startswith('minute'):
                        sleep_duration = duration_value * 60
                    elif unit.startswith('second'):
                        sleep_duration = duration_value
                    else:
                        print("Unknown unit specified.")
                        external_speak("Unknown unit specified.")
                        return

                    self.go_to_sleep(command)
                else:
                    print("Command not recognized.")
                    external_speak("Command not recognized.")

            except ValueError:
                print("Invalid command format for sleep duration.")
                external_speak("Invalid command format for sleep duration.")

        elif "remember this" in command:
            self.remember_this(command)
        elif "alpha view" in command:
            self.start_target_program(command)
        elif "password generator" in command:
            self.start_Alpha_Gen(command)
        elif "maps" in command:
            self.open_maps()

        elif "exit" in command:
            self.exit()

        elif "install " in command:
            self.install_application(command)
        elif command.startswith("ask Wolfram"):
            query = command[len("ask Wolfram"):].strip()  # Extract the query
            self.ask_wolfram(query)
        elif "alpha install" in command:
            self.install_application_winget(command)
        elif "who created you" in command:
            self.creator(command)
        elif "Alpha say hi" in command:
            self.hi(command)
        elif "i am doing ok" in command:
            self.remark(command)
        elif "what is your name" in command:
            self.name(command)
        elif "what is your purpose" in command:
            self.purpose(command)
        elif 'open' in command.lower():
            # Use regular expression to extract application name after "open"
            match = re.search(r'open\s+(.+)', command, re.IGNORECASE)
            if match:
                application_name = match.group(1).strip().replace(" ", "_")  # Extract and normalize application name
                self.access_application_or_install('access', application_name)
            else:
                print("Invalid command format.")
        else:
            self.secondary_command(command)  # Query Wolfram Alpha for general questions


    @staticmethod
    def calculate(command):
        # Calculate mathematical expression using Wolfram Alpha
        expression = command.replace("calculate", "").strip()
        
        try:
            # Query Wolfram Alpha
            res = wolfram_alpha_client.query(expression)
            
            # Check if results are available
            if res.results:
                try:
                    # Attempt to get the result
                    answer = next(res.results).text
                except StopIteration:
                    # Handle the case where results are exhausted
                    answer = "Sorry, I couldn't calculate that."
            else:
                # Handle the case where there are no results
                answer = "Sorry, I couldn't calculate that."
        
        except Exception as e:
            # Handle any other exceptions that might occur
            answer = f"An error occurred: {str(e)}"
        
        print(f"Calculation result: {answer}")
        external_speak(answer)


    @staticmethod
    def calculate_wolfram(query):
        res = wolfram_alpha_client.query(query)
        answer = next(res.results).text
        return answer

    def activate(self):
        if not self.active:
            self.suspend_assistant()  # Call suspend_assistant if deactivated
        self.active = True
        return "Assistant activated."

    def deactivate(self):
        if not self.active:
            self.unsuspend_assistant()
        self.active = False
        return "Assistant deactivated."

    @staticmethod
    def open_website(command):
        # Open a website based on user command
        website = re.search('website (.+)', command).group(1)
        url = f"https://www.{website}.com"
        webbrowser.open(url)
        print(f"Opening website: {url}")

    @staticmethod
    def search_web(command):
        # Search the web using user command
        query = re.search('search for (.+)', command).group(1)
        url = f"https://www.google.com/search?q={quote(query)}"
        webbrowser.open(url)
        print(f"Searching the web for: {query}")

    @staticmethod
    def tell_about(command):
        topic = re.search(r'tell me about (.+)', command).group(1)
        try:
            summary = wikipedia.summary(topic, sentences=2)
            print(f"Here is what I found about {topic}: {summary}")
            external_speak(summary)
        except wikipedia.exceptions.DisambiguationError as e:
            print(f"DisambiguationError: {e}")
            external_speak("There were multiple matches. Please be more specific.")
        except wikipedia.exceptions.PageError as e:
            print(f"PageError: {e}")
            external_speak("I could not find any information on that topic.")

    def remember_this(self, command):
        try:
            # Extract memory data from the command
            memory_data = self.extract_memory_data(command)

            # Store memory data
            self.store_short_term_memory(memory_data)

            # Log memory data
            self.log_memory(memory_data)

            # Confirm memory storage to user
            self.confirm_memory_storage()

            # Update in-memory lists of memories
            self.update_memories(memory_data)

        except Exception as e:
            logging.error(f"An error occurred while processing the command: {e}")

    @staticmethod
    def extract_memory_data(command):
        """Extract the memory data from the command."""
        return command.split("remember", 1)[-1].strip()

    def store_short_term_memory(self, memory_data):
        """Store the memory data in short-term memory."""
        # Implementation for storing short-term memory
        pass

    @staticmethod
    def log_memory(memory_data):
        """Log memory data to a file."""
        log_message = f"[Memory] {memory_data}\n"
        with open("assistant_log.txt", "a") as log_file:
            log_file.write(log_message)

    @staticmethod
    def confirm_memory_storage():
        """Inform the user that the memory has been stored."""
        external_speak("I will remember that.")

    def update_memories(self, memory_data):
        """Update the in-memory list of memories."""
        if 'memories' not in self.__dict__:
            self.memories = []
        self.memories.append(memory_data)

    def remind_users(self):
        """Remind users of all stored memories."""
        if self.memories:
            for memory in self.memories:
                external_speak(f"Remember this: {memory}")

    def clear_memories(self):
        """Clear all stored memories."""
        self.memories.clear()
        external_speak("All stored memories have been deleted.")

    def suspend_assistant(self):
        self.suspended = True
        external_speak("Assistant suspended.")
        print("Assistant is suspended.")
        self.listen_for_unsuspend()

    def unsuspend_assistant(self):
        self.suspended = False
        external_speak("Assistant activated.")
        print("Assistant is active.")

    def listen_for_unsuspend(self):
        """Listen for the 'unsuspend' command while the assistant is suspended."""
        while self.suspended:
            with sr.Microphone() as source:
                recognizer.adjust_for_ambient_noise(source)
                print()
                audio = recognizer.listen(source)

            try:
                print()
                text = recognizer.recognize_google(audio)
                print(f"User said: {text}")

                if 'unsuspend' in text.lower():
                    self.unsuspend_assistant()
            except sr.UnknownValueError:
                print()
            except sr.RequestError as e:
                print(f"Could not request results from Google Speech Recognition service; {e}")

            time.sleep(1)  # Small delay to prevent excessive CPU usage

    def recall_memories(self):
        # Recall and possibly speak out all stored memories
        if self.memories:
            external_speak("Here are the memories I have:")
            for index, memory in enumerate(self.memories, start=1):
                external_speak(f"Memory {index}: {memory}")
        else:
            external_speak("I don't seem to have any memories right now.")

    @staticmethod
    def shutdown():
        print("Shutting down...")
        # Perform shutdown actions here if needed
        os.system("shutdown /s /t 1")

    @staticmethod
    def creator(command):
        print(f"Mr Samuel Great")
        external_speak("Mr Samuel Great")
        return None
    
    @staticmethod
    def purpose(command):
        print(f"To Guide and aid humans, helping them achieve greater things. as it says in my name Alpha which stands for another learning powered human aid. my mission human preservation")
        external_speak("To Guide and aid humans, helping them achieve  greater things. as it says in my name Alpha which stands for another learning powered human aid. my mission human preservation")

    @staticmethod
    def name(command):
        print(f"My name is Alpha")
        external_speak("My Name is Alpha")
    
    @staticmethod
    def hi(command):
        external_speak("hello sir how are you doing, i have heard so much about you it is a pleasure to meet you.")

    @staticmethod
    def remark(command):
        print(f"thats good to hear, how may i help you today")
        external_speak("thats good to hear, how may i help you today.")
    
    def greet_and_respond(self, command):
        if not isinstance(self, str):
            return "Hello sir."

        greetings = ["hello Alpha", "hi Alpha", "hey Alpha", "who created you", "greetings Alpha"]
        responses = ["Hello sir!", "Hi sir!", "Hey sir!", "mr samuel great", "Hello to you too sir!"]

        # Normalize input by converting to lowercase
        self = self.lower()

        # Check if the self is in our list of recognized greetings
        if any(self in s for s in greetings):
            return random.choice(responses)
        else:
            return "I'm sorry, I don't understand that self."

    @staticmethod
    def start_target_program(command):
        # Get the path to the current directory
        current_dir = os.path.dirname(__file__)
        target_script = os.path.join(current_dir, 'CONTROL_PANEL\ControlPanel.exe')

        # Start the target program
        subprocess.Popen([target_script], shell=True)
        external_speak("Starting Alpha View")

    @staticmethod
    def start_Alpha_Gen(command):
        # Get the path to the current directory
        current_dir = os.path.dirname(__file__)
        target_script = os.path.join(current_dir, 'PASS_GEN\Alpha_Pass.exe')

        # Start the target program
        subprocess.Popen([target_script], shell=True)
        external_speak("Starting Alpha Gen")

    def exit(self):
        # Shutdown assistant (exit program)
        print("Shutting down assistant.")
        self.log_file.close()
        exit()

    @staticmethod
    def Good_bye():
        # Placeholder for shutting down assistant operations
        print("Shutting down assistant.")
        external_speak("Good bye sir.")
        exit()

    def active(self):
        while True:
            if not self.active:
                self.unsuspend_assistant()
            else:
                self.suspend_assistant()
            time.sleep(1)

    def go_to_sleep(self, command):
        try:
            # Extract the duration from the command
            match = re.search(r'hibernate for (\d+) (seconds|minutes|hours)', command)
            if not match:
                raise ValueError("Command format is incorrect. Expected format: 'hibernate for <duration> <unit>'.")

            duration_value = int(match.group(1))
            duration_unit = match.group(2)

            # Convert the duration to seconds for sleep function
            if duration_unit == "minutes":
                duration_value *= 60
            elif duration_unit == "hours":
                duration_value *= 3600
            elif duration_unit != "seconds":
                raise ValueError(f"Unsupported unit of time: {duration_unit}")

            print(f"Hibernating for {duration_value} seconds...")
            external_speak(f"Hibernating for {duration_value} seconds...")
            self.is_sleeping = True
            self.sleep_event.clear()
            time.sleep(duration_value)
            self.is_sleeping = False
            print("Hibernation complete.")
            external_speak(
                f"Hibernation for {duration_value // 60} minutes is complete.")  # Converted to minutes for speech

        except ValueError as ve:
            print(f"Invalid command format: {ve}")
            external_speak(
                "I'm sorry, I didn't catch that. Please specify the duration and unit in the correct format.")
        except Exception as e:
            print(f"Error hibernating: {e}")
            external_speak("Sorry, there was an error hibernating.")

    @staticmethod
    def sleep():
        print("Going to sleep...")
        # Perform sleep actions here if needed
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

    @staticmethod
    def get_time():
        current_time = datetime.datetime.now().strftime("%I:%M:%S %p")
        print(f"The current time is {current_time}")
        external_speak(f"The current time is {current_time}")

    @staticmethod
    def get_date():
        year = datetime.datetime.now().year
        month = datetime.datetime.now().strftime("%B")
        day = datetime.datetime.now().day
        print(f"Today is {month} {day}, {year}")
        external_speak(f"Today is {month} {day}, {year}")

    @staticmethod
    def ask_wolfram(query):
        try:
            res = wolfram_alpha_client.query(query)
            answer = next(res.results).text
            print(f"Wolfram Alpha says: {answer}")
            external_speak(answer)
        except Exception as e:
            print(f"Error fetching results from Alpha: {str(e)}")
            external_speak("Sorry, I couldn't fetch the answer for you.")

    @staticmethod
    def wish_me():
        hour = datetime.datetime.now().hour
        if 6 <= hour < 12:
            external_speak("Good morning Sir!")
        elif 12 <= hour < 18:
            external_speak("Good afternoon Sir!")
        elif 18 <= hour < 24:
            external_speak("Good evening Sir!")
        else:
            external_speak("Hello!")

        external_speak("Alpha At your service. How may I assist you?")

    def process_command(self, command):
        # Handle specific commands
        if 'time' in command:
            self.get_time()
        elif 'date' in command:
            self.get_date()
        elif 'remember' in command:
            # Extract the memory data from the command
            memory_data = command.split('remember', 1)[-1].strip()
            self.remember_this(memory_data)
        elif 'recall' in command:
            self.recall_memories()
        elif 'access' in command or 'install' in command:
            # Use regular expression to extract application name after "install"
            match = re.search(r'install\s+(.+)', command, re.IGNORECASE)
            if match:
                application_name = match.group(1).strip().replace(" ", "_")  # Extract and normalize application name
                self.install_application(command)
                self.install_application_winget(command)

        elif 'news' in command:
            # Extract the command after 'news'
            match = re.search(r'news\s*(.+)?', command, re.IGNORECASE)
            if match:
                news_command = match.group(1)  # This captures the words after 'news'
                # Process the news command here (e.g., fetching news based on news_command)
                self.fetch_and_display_news(news_command)
        elif 'maps' in command.lower():
            # Split command to find the part after 'maps'
            parts = command.lower().split('maps', 1)
            if len(parts) > 1:
                location = parts[1].strip()
                
                if location:
                    # Construct the Google Maps URL with the search query
                    search_query = quote(location)
                    map_url = f"https://www.google.com/maps/search/?api=1&query={search_query}"
                    
                    # Open the map URL in a web browser
                    webbrowser.open(map_url)
                else:
                    print("No location was provided after 'maps'.")
            else:
                print("No location found in the command.")
        elif "open" in command.lower():
            match = re.search(r'open\s+(.+)', command, re.IGNORECASE)
            if match:
                application_name = match.group(1).strip()  # Extract application name
                self.open_existing_application(application_name)
            else:
                print("Invalid command format.")
                external_speak("Invalid command format.")

        elif "activate" in command:
            self.active = True
            external_speak("Assistant activated.")
        elif "deactivate" in command:
            self.active = False
            external_speak("Assistant deactivated.")
        elif "set alarm" in command:
            self.set_alarm(command)

        else:
            self.process_speech_command(command)

    def log_message(self, message):
        # Log messages to a file
        self.log_file.write(f"{datetime.datetime.now()}: {message}\n")
        self.log_file.flush()

    def close_log(self):
        # Close the log file
        self.log_file.close()

    def assess_complexity(self, command):
        """
        Assess the complexity of the command.
        This is a placeholder for complexity assessment logic.
        For example, you might check for the length of the command,
        the presence of specific keywords, or other factors.
        """
        # Placeholder complexity calculation logic
        complexity_score = len(command)  # Simple example: use command length as a proxy for complexity

        # Set a threshold value for complexity; this value is just an example
        self.COMPLEXITY_THRESHOLD = 50  # Define this value based on your needs
        
        return complexity_score
    
    def secondary_command(self, command):
        complexity = self.assess_complexity(command)
        if complexity > self.COMPLEXITY_THRESHOLD:
            Brain.ask_wolfram(command)  # Correctly call the static method
        elif 'play' in command:
            self.handle_music_command(command)
        elif 'increase volume' in command:
            self.change_volume('increase')
        elif 'decrease volume' in command:
            self.change_volume('decrease')
        elif 'mute' in command:
            self.change_volume('mute')
        elif 'undo' in command:
            self.change_volume('undo')
        elif 'increase brightness' in command:
            self.change_brightness('increase')
        elif 'decrease brightness' in command:
            self.change_brightness('decrease')
        elif 'turn on Wi-Fi' in command:
            self.control_wifi('turn on')
        elif 'turn off Wi-Fi' in command:
            self.control_wifi('turn off')
        elif 'turn on Bluetooth' in command:
            self.control_bluetooth('turn on')
        elif 'turn off Bluetooth' in command:
            self.control_bluetooth('turn off')
        elif 'enable online security' in command:
            self.defense(command)
        elif 'box' in command:
            self.alpha_hub(command)
        elif 'workstation' in command:
            self.alpha_suite(command)
        elif 'help' in command:
            self.alpha_help(command)
        elif 'look up' in command:
            self.lookup(command)
        elif 'password manager' in command:
            self.maneger(command)
        elif 'start code 255' in command:
            self.code255(command)
        elif 'start code 236' in command:
            self.code236(command)
        elif 'alpha CMD' in command:
            self.ALCMD(command)
        elif 'start passing time' in command:
            self.game(command)
        else:
            self.handle_fallback(command)  # Query Wolfram Alpha for general questions
            
    def change_volume(self, action):
        # Fixed volume increment/decrement
        amount = 10000  # This is equivalent to 10 units in nircmd

        if action == 'increase':
            subprocess.run(["nircmd.exe", "changesysvolume", str(amount)])
            print("Volume increased by 10 units")
            external_speak("Volume Increased")
        elif action == 'decrease':
            subprocess.run(["nircmd.exe", "changesysvolume", str(-amount)])
            print("Volume decreased by 10 units")
            external_speak("Volume Decreased")
        elif action == 'mute':
            subprocess.run(["nircmd.exe", "mutesysvolume", "1"])
            print("Volume is muted")
        elif action == 'undo':
            subprocess.run(["nircmd.exe", "mutesysvolume", "0"])
            print("Volume is unmuted")
        else:
            print("Invalid action. Use 'increase', 'decrease', 'mute', or 'undo'.")

    def change_brightness(self, action):
        # Fixed brightness increment/decrement
        amount = 10  # Amount to change brightness (can be adjusted)

        if action == 'increase':
            subprocess.run(["nircmd.exe", "changebrightness", str(amount)])
            print("Brightness increased by 10 units")
            external_speak("Brightness Increased")
        elif action == 'decrease':
            subprocess.run(["nircmd.exe", "changebrightness", str(-amount)])
            print("Brightness decreased by 10 units")
            external_speak("Brightness Decreased")
        else:
            print("Invalid action. Use 'increase' or 'decrease'.")

    def control_wifi(self, action):
        if action == 'turn on':
            command = 'Enable-NetAdapter -Name "Wi-Fi"'
        elif action == 'turn off':
            command = 'Disable-NetAdapter -Name "Wi-Fi"'
        else:
            print("Invalid action. Use 'turn on' or 'turn off'.")
            return

        # Run PowerShell command to control Wi-Fi
        subprocess.run(["powershell", "-Command", command])
        print(f"Wi-Fi has been {action}")

    def control_bluetooth(self, action):
        if action == 'turn on':
            command = 'Start-Service bthserv'
        elif action == 'turn off':
            command = 'Stop-Service bthserv -Force'
        else:
            print("Invalid action. Use 'turn on' or 'turn off'.")
            return

        # Run PowerShell command to control Bluetooth
        subprocess.run(["powershell", "-Command", command])
        print(f"Bluetooth has been {action}")

    def set_alarm(self, command):
        print("set_alarm called with command:", command)  # Debugging statement

        # Check if the command has already been processed
        if command in self.processed_commands:
            print("Command already processed.")
            return
        
        match = re.search(r'set alarm to (\d{1,2}:\d{2} (?:a\.m\.|p\.m\.))', command, re.IGNORECASE)
        if match:
            alarm_time = match.group(1)
            self.alarm_time_12 = alarm_time
            self.alarm_time_24 = self.convert_to_24_hour_format(alarm_time)
            if self.alarm_time_24:
                print(f"Alarm set for {alarm_time}")
                external_speak(f"Alarm set for {alarm_time}")
                self.alarm_set = True
                self.processed_commands.add(command)  # Mark this command as processed
                # Start the alarm clock in a new thread
                threading.Thread(target=self.alarm_clock, daemon=True).start()
            else:
                print("Invalid time format.")
                external_speak("Invalid time format.")
        else:
            print("Please say the alarm time in the correct format (e.g., 07:30 a.m. or 07:30 p.m.).")
            external_speak("Please say the alarm time in the correct format (e.g., 07:30 a.m. or 07:30 p.m.).")

    def set_alarm_thread(self, command):
        print("set_alarm_thread called with command:", command)  # Debugging statement
        # Use a lock to ensure thread safety when accessing processed_commands
        with threading.Lock():
            threading.Thread(target=self.set_alarm, args=(command,), daemon=True).start()

    @staticmethod
    def convert_to_24_hour_format(alarm_time):
        match = re.match(r'(\d{1,2}):(\d{2}) (a\.m\.|p\.m\.)', alarm_time, re.IGNORECASE)
        if match:
            hour, minute, period = int(match.group(1)), int(match.group(2)), match.group(3).lower()
            if period == 'p.m.' and hour != 12:
                hour += 12
            elif period == 'a.m.' and hour == 12:
                hour = 0
            return f"{hour:02d}:{minute:02d}"
        return None

    def alarm_clock(self):
        """Function to set off an alarm at the specified time."""
        print("Alarm clock thread started")  # Debugging statement
        while self.alarm_set:
            current_time = datetime.datetime.now().strftime("%H:%M")  # Current time in 24-hour format
            if current_time == self.alarm_time_24:
                print("Time to wake up!")
                self.alarm_triggered.set()  # Set the event flag
                self.play_alarm_sound()
                self.alarm_set = False  # Disable the alarm after it goes off
                break
            time.sleep(60)

    def play_alarm_sound(self):
        if self.alarm_sound_file:
            try:
                sound = AudioSegment.from_file(self.alarm_sound_file)
                play(sound)
            except Exception as e:
                print(f"Error playing sound: {e}")
        else:
            print("No alarm sound file set.")

    def check_alarm(self):
        """This function runs in the main thread and checks if the alarm has triggered."""
        print("Checking alarm...")  # Debugging statement
        while True:
            self.alarm_triggered.wait()  # Wait until the event flag is set
            external_speak("Time to wake up!")
            self.alarm_triggered.clear()  # Reset the event flag for the next alarm

    def get_youtube_video_url(self, query):
        videos_search = VideosSearch(query, limit=1)
        results = videos_search.result()
        if results['result']:
            video_url = results['result'][0]['link']
            return video_url
        return None

    def play_music(self, platform, music_name):
        if platform.lower() == "spotify":
            results = self.sp.search(q=music_name, limit=1, type="track")
            if results['tracks']['items']:
                track_uri = results['tracks']['items'][0]['uri']
                try:
                    self.sp.start_playback(uris=[track_uri])
                    print(f"Playing '{music_name}' on Spotify.")
                except spotipy.exceptions.SpotifyException as e:
                    print(f"Error starting playback: {e}")
            else:
                print(f"Could not find '{music_name}' on Spotify.")

        elif platform.lower() == "youtube":
            search_query = f"{music_name} music"
            video_url = self.get_youtube_video_url(search_query)

            if video_url:
                webbrowser.open(video_url)
                print(f"Playing '{music_name}' on YouTube.")
            else:
                print(f"Could not find '{music_name}' on YouTube.")

    def handle_music_command(self, text):
        parts = text.lower().split(" on ")
        if len(parts) == 2:
            music_name = parts[0].replace("play", "").strip()
            platform = parts[1].strip()
            self.play_music(platform, music_name)

    @staticmethod
    def access_application_or_install(action, application_name):
        try:
            if action == 'access':
                # Handle application access based on the platform
                if platform.system() == 'Windows':
                    if application_name.lower() == 'chrome':
                        subprocess.Popen(['start', 'chrome'], shell=True)
                    elif application_name.lower() == 'firefox':
                        subprocess.Popen(['start', 'firefox'], shell=True)
                    elif application_name.lower() == 'edge':
                        subprocess.Popen(['start', 'microsoft-edge:'], shell=True)
                    elif application_name.lower() == 'ie' or application_name.lower() == 'internet explorer':
                        subprocess.Popen(['start', 'iexplore'], shell=True)
                    elif application_name.lower() == 'notepad':
                        subprocess.Popen(['start', 'notepad'], shell=True)
                    elif application_name.lower() == 'calculator':
                        subprocess.Popen(['start', 'calc'], shell=True)
                    elif application_name.lower() == 'explorer' or application_name.lower() == 'file explorer':
                        subprocess.Popen(['start', 'explorer'], shell=True)
                    elif application_name.lower() == 'control panel':
                        subprocess.Popen(['start', 'control'], shell=True)
                    elif application_name.lower() == 'task manager':
                        subprocess.Popen(['start', 'taskmgr'], shell=True)
                    elif application_name.lower() == 'settings' or application_name.lower() == 'windows settings':
                        subprocess.Popen(['start', 'ms-settings:'], shell=True)
                    # Add more applications as needed
                    else:
                        print(f"Error: Application '{application_name}' not supported or recognized on Windows.")
                        external_speak(
                            f"Error: Application '{application_name}' not supported or recognized on Windows.")

                elif platform.system() == 'Darwin':  # macOS
                    if application_name.lower() == 'chrome':
                        subprocess.Popen(['open', '-a', 'Google Chrome'])
                    elif application_name.lower() == 'firefox':
                        subprocess.Popen(['open', '-a', 'Firefox'])
                    # Add more applications as needed
                    else:
                        print(f"Error: Application '{application_name}' not supported or recognized on macOS.")

                elif platform.system() == 'Linux':
                    if application_name.lower() == 'chrome':
                        subprocess.Popen(['google-chrome'])
                    elif application_name.lower() == 'firefox':
                        subprocess.Popen(['firefox'])
                    # Add more applications as needed
                    else:
                        print(f"Error: Application '{application_name}' not supported or recognized on Linux.")

                else:
                    print(
                        f"Error: Unsupported platform '{platform.system()}'. Cannot access application '{application_name}'.")

            elif action == 'install':
                # Implement logic to install the specified application
                pass  # Placeholder for installation logic

        except Exception as e:
            print(f"Error handling '{action}' for application '{application_name}': {str(e)}")

    def defense(self, command):
    # Ensure AlphaDefense.cyber_defense_main is callable as a script or modify accordingly
        try:
            # Use subprocess to run the command
            result = subprocess.run(['AlphaDefense.exe'], capture_output=True, text=True)
            external_speak('AlphaDefence is open sir!')
            # Print or handle the output and error if needed
            print('Output:', result.stdout)
            print('Error:', result.stderr)
            result.check_returncode()  # Raises CalledProcessError if the return code was non-zero
        except subprocess.CalledProcessError as e:
            print(f'An error occurred: {e}')
        except FileNotFoundError:
            print('AlphaDefence was not found.')
            external_speak('AlphaDefence was not found.')

    def alpha_suite (self, command):
    
        try:
            # Use subprocess to run the command
            subprocess.Popen(['AlphaSuite.exe'])
            external_speak('Alpha suite is open sir!')
            
        except FileNotFoundError:
            print('Alpha suite was not found.')
            external_speak('Alpha suite was not found.')

    def alpha_hub (self, command):
    
        try:
            # Use subprocess to run the command
            subprocess.Popen(['AlphaHub.exe'])
            external_speak('Alpha Hub is open sir!')
            
        except FileNotFoundError:
            print('Alpha Hub was not found.')
            external_speak('Alpha Hub was not found.')

    def alpha_help (self, command):
    
        try:
            # Use subprocess to run the command
            subprocess.Popen(['AlphaCommands.exe'])
            external_speak('Alpha Help is open sir!, feel free to use any of the commands present to interacte with me')
            
        except FileNotFoundError:
            print('Alpha Help was not found.')
            external_speak('Alpha Help was not found.')

    def lookup (self, command):
    
        try:
            # Use subprocess to run the command
            subprocess.Popen(['AlphaOsint.exe'])
            external_speak('osint is open sir')
            
        except FileNotFoundError:
            print('osint was not found.')
            external_speak('osint was not found.')

    def maneger (self, command):
    
        try:
            # Use subprocess to run the command
            subprocess.Popen(['AlphaPasswordManeger.exe'])
            external_speak('password manager  is open sir')
            
        except FileNotFoundError:
            print('password manager was not found.')
            external_speak('password manager was not found.')

    def code255 (self, command):
    
        try:
            # Use subprocess to run the command
            subprocess.Popen(['ALT255.exe'])
            external_speak('system info gathering is running sir')
            
        except FileNotFoundError:
            print('ALT255 was not found.')
            external_speak('ALT255 was not found.')
    
    def code236 (self, command):
    
        try:
            # Use subprocess to run the command
            subprocess.Popen(['ALT236.exe'])
            external_speak('fail safe is running sir')
            
        except FileNotFoundError:
            print('ALT236 was not found.')
            external_speak('ALT236 was not found.')

    def ALCMD (self, command):
    
        try:
            # Use subprocess to run the command
            subprocess.Popen(['Alpha_cmd.exe'])
            external_speak('Command line is open sir')
            
        except FileNotFoundError:
            print('Alpha_cmd was not found.')
            external_speak('Alpha_cmd was not found.')

    def game (self, command):
    
        try:
            # Use subprocess to run the command
            subprocess.Popen(['Alpha_Game.exe'])
            external_speak('passing time is open sir')
            
        except FileNotFoundError:
            print('passing time was not found.')
            external_speak('passing time was not found.')

    @staticmethod
    def open_existing_application(application_name):
        try:
            os_system = platform.system()  # Get the operating system
            application_name = application_name.lower()

            if os_system == 'Windows':
                applications = {
                    'chrome': 'chrome',
                    'firefox': 'firefox',
                    'edge': 'microsoft-edge:',
                    'ie': 'iexplore',
                    'internet explorer': 'iexplore',
                    'notepad': 'notepad',
                    'calculator': 'calc',
                    'explorer': 'explorer',
                    'file explorer': 'explorer',
                    'control panel': 'control',
                    'task manager': 'taskmgr',
                    'settings': 'ms-settings:',
                    'windows settings': 'ms-settings:'
                }
                command = applications.get(application_name)
                if command:
                    subprocess.Popen(['start', command], shell=True)
                    print(f"Opening {application_name}.")
                    external_speak(f"Opening {application_name}.")
                else:
                    print(f"Error: Application '{application_name}' not supported or recognized on Windows.")
                    external_speak(f"Error: Application '{application_name}' not supported or recognized on Windows.")

            elif os_system == 'Darwin':  # macOS
                applications = {
                    'chrome': 'Google Chrome',
                    'firefox': 'Firefox',
                    'safari': 'Safari'
                }
                app_name = applications.get(application_name)
                if app_name:
                    subprocess.Popen(['open', '-a', app_name])
                    print(f"Opening {application_name}.")
                    external_speak(f"Opening {application_name}.")
                else:
                    print(f"Error: Application '{application_name}' not supported or recognized on macOS.")
                    external_speak(f"Error: Application '{application_name}' not supported or recognized on macOS.")

            elif os_system == 'Linux':
                applications = {
                    'chrome': 'google-chrome',
                    'firefox': 'firefox'
                }
                command = applications.get(application_name)
                if command:
                    subprocess.Popen([command])
                    print(f"Opening {application_name}.")
                    external_speak(f"Opening {application_name}.")
                else:
                    print(f"Error: Application '{application_name}' not supported or recognized on Linux.")
                    external_speak(f"Error: Application '{application_name}' not supported or recognized on Linux.")

            else:
                print(f"Error: Unsupported platform '{os_system}'. Cannot open application '{application_name}'.")
                external_speak(
                    f"Error: Unsupported platform '{os_system}'. Cannot open application '{application_name}'.")

        except Exception as e:
            print(f"Error opening application '{application_name}': {str(e)}")
            external_speak(f"Error opening application '{application_name}': {str(e)}")

    @staticmethod
    def install_application(command):
        # Example: Install application using subprocess
        application_name = re.search(r'install (.+)', command).group(1)
        try:
            subprocess.run(['winget', 'install', application_name], check=True)
            external_speak(f"{application_name} has been installed.")
        except subprocess.CalledProcessError as e:
            print(f"Error installing application: {e}")
            external_speak(f"There was an error installing {application_name}.")

    @staticmethod
    def install_application_winget(command):
        # Example: Install application using winget
        application_name = re.search(r'install (.+)', command).group(1)
        try:
            # Run the winget command
            result = subprocess.run(['winget', 'show', application_name, '--exact', '--source', 'winget'],
                                    capture_output=True, text=True)

            if result.returncode == 0:
                # Extract the latest package ID from the output
                packages = re.findall(r'(?<=Id\s)(\S+)', result.stdout)
                if packages:
                    latest_package_id = packages[-1]  # Get the last package ID (assuming it's the latest)

                    # Install the latest package
                    install_result = subprocess.run(['winget', 'install', latest_package_id], capture_output=True,
                                                    text=True)

                    if install_result.returncode == 0:
                        external_speak(f"{application_name} has been installed.")
                    else:
                        print(f"Error installing application: {install_result.stderr.strip()}")
                        external_speak(f"There was an error installing {application_name}.")
                else:
                    print(f"No package found for {application_name}.")
                    external_speak(f"No package found for {application_name}.")
            else:
                print(f"Error fetching package information: {result.stderr.strip()}")
                external_speak(f"There was an error fetching package information for {application_name}.")
        except subprocess.CalledProcessError as e:
            print(f"Error installing application: {e}")
            external_speak(f"There was an error installing {application_name}.")

    def run_assistant(self):
        self.wish_me()
        while True:
            if not self.suspended:
                command = self.recognize_speech()
                if command:
                    self.process_command(command)
            time.sleep(1)

    # Add a slight delay to prevent excessive CPU usage
    @staticmethod
    def fetch_and_display_news(news_category=None):
        try:
            # Check if a news category was provided; if not, default to general news
            if news_category:
                # Open the news category URL in the default web browser
                google_news_url = f'https://news.google.com/{news_category}'
                webbrowser.open(google_news_url, new=2)
                print(f"Opening {news_category} news in the browser.")
                external_speak(f"Opening {news_category} news in the browser.")
            else:
                # Fetch news from Google News RSS feed
                url = "https://news.google.com/rss?hl=en-IN&gl=IN&ceid=IN:en"
                response = requests.get(url)
                content = response.content
                soup = BeautifulSoup(content, "html.parser")
                articles = soup.findAll("item")

                # Construct the news summary
                speak_news = "The news for today are as follows:"
                for i, article in enumerate(articles, start=1):
                    if i > 5:  # Limit to top 5 news articles
                        break
                    title = article.find("title").text
                    speak_news += f" {i}. {title}. "

                # Speak out the news summary
                external_speak(speak_news)
                print(speak_news)

        except Exception as e:
            print(f"Error: {e}")
            external_speak(f"An error occurred while fetching the news: {e}")

    @staticmethod
    def open_news_in_browser(news_category):
        # Define the Google News URL based on the news category
        google_news_url = f'https://news.google.com/{news_category}'

        try:
            # Open the news URL in the default web browser
            webbrowser.open(google_news_url, new=2)

        except Exception as e:
            print(f"Error opening news in browser: {e}")

    def store_short_term_memory(self, memory):
        # Store short-term memory into SQLite database
        timestamp = int(time.time())
        memory_data = json.dumps({"text": memory})
        self.short_term_cursor.execute("INSERT INTO short_term_memory (timestamp, memory_data) VALUES (?, ?)",
                                       (timestamp, memory_data))
        self.short_term_conn.commit()
    
    def scrape_website(url):
        # Send a GET request to the URL
        response = requests.get(url)

        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            # Parse the content of the page with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')

            # Example: Extracting all the links from the page
            links = soup.find_all('a')

            # Print out all the links found
            for link in links:
                print(link.get('href'))

        else:
            print('Failed to retrieve the webpage. Status code:', response.status_code)

    # Example usage:
    url = 'https://Google.com'
    scrape_website(url)

    def short_term_memory(self):
        # Retrieve short-term memory from SQLite database
        self.short_term_cursor.execute("SELECT * FROM short_term_memory ORDER BY timestamp DESC LIMIT 1")
        result = self.short_term_cursor.fetchone()
        if result:
            return json.loads(result[1])['text']
        else:
            return ""

    @staticmethod
    def process_api_response(api_response):
        # Placeholder for processing API responses asynchronously
        print(f"Processing API response: {api_response}")
        # Add your processing logic here

    @staticmethod
    def process_system_event(system_event):
        # Placeholder for processing system events asynchronously
        print(f"Processing system event: {system_event}")
        # Add your processing logic here

    @staticmethod
    def process_sensor_data(sensor_data):
        # Placeholder for processing sensor data asynchronously
        print(f"Processing sensor data: {sensor_data}")
        # Add your processing logic here

    def wake(self):
        """Wake up the assistant immediately."""
        if self.is_sleeping:
            print("Waking up the assistant...")
            external_speak("Waking up now...")
            self.is_sleeping = False
            self.sleep_event.set()  # Ensure that any waiting on the sleep event is notified
        else:
            print("The assistant is already awake.")
            external_speak("I am already awake.")

    def listen_for_wake_word(self):
        """Continuously listen for the wake word."""
        while self.is_sleeping:
            with microphone as source:
                recognizer.adjust_for_ambient_noise(source)
                print("Listening for wake word...")
                external_speak("Listening for wake word...")  # Notify that it's listening

                audio = recognizer.listen(source)

            try:
                print("Recognizing...")
                text = recognizer.recognize_google(audio)
                print(f"User said: {text}")

                if 'wake' in text.lower():
                    self.wake()  # Wake the assistant up
            except sr.UnknownValueError:
                print("Google Speech Recognition could not understand audio")
            except sr.RequestError as e:
                print(f"Could not request results from Google Speech Recognition service; {e}")

        # Sleep briefly to avoid high CPU usage
        time.sleep(1)

    def store_long_term_memory(self, key, recent_memory):
        pass


if __name__ == "__main__":
    # Initialize Brain with intelligence level
    my_brain = Brain(intelligence=0.6)
    
    my_brain.run_assistant()
    
