import pyttsx3
import datetime
import speech_recognition as sr
import os
import webbrowser
import requests
from bs4 import BeautifulSoup
import re
import sqlite3
import subprocess
import torch
import smtplib
import pyjokes
import wikipedia
from twilio.rest import Client
import psutil
import wolframalpha
from transformers import GPT2LMHeadModel, GPT2Tokenizer
import spacy
import threading

# Initialize text-to-speech engine with more human-like voice
# engine = pyttsx3.init()
# voices = engine.getProperty('voices')
# engine.setProperty('voice', voices[1].id)  # Index 1 is a female voice, choose based on preference

tts_engine = pyttsx3.init()
tts_lock = threading.Lock()  # Lock for TTS access
voices = tts_engine.getProperty('voices')
tts_engine.setProperty('voice', voices[1].id)  # Set to the desired voice


# Persistent state variables
current_context = None
database_file = 'assistant_db.sqlite'

# Initialize SQLite database connection
conn = sqlite3.connect(database_file)
c = conn.cursor()

# Initialize GPT-2 model and tokenizer
model_name = 'gpt2'
tokenizer = GPT2Tokenizer.from_pretrained(model_name)
model = GPT2LMHeadModel.from_pretrained(model_name)

# Set up model parameters
max_length = 100
device = 'cuda' if torch.cuda.is_available() else 'cpu'  # Use GPU if available
model.to(device)  # Move model to appropriate device

# Initialize Wolfram Alpha API
wolfram_alpha_app_id = 'your_wolfram_alpha_app_id'
wolfram_alpha_client = wolframalpha.Client(wolfram_alpha_app_id)

# Load English tokenizer, tagger, parser, NER and word vectors
nlp = spacy.load("en_core_web_sm")


# Function to initialize SQLite database
def initialize_database():
    c.execute('''CREATE TABLE IF NOT EXISTS activities
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT, activity TEXT)''')
    c.execute('''CREATE TABLE IF NOT EXISTS memories
                  (id INTEGER PRIMARY KEY AUTOINCREMENT, context TEXT, key TEXT, value TEXT, timestamp TEXT)''')
    conn.commit()


# Function to speak the given audio with more natural human-like voice
# def speak(audio):
    #engine.say(audio)
    #engine.runAndWait()

def speak(audio):
        with tts_lock:  # Ensure only one thread accesses the TTS engine
            tts_engine.say(audio)
            tts_engine.runAndWait()

# Function to get current time and speak it
def get_time():
    current_time = datetime.datetime.now().strftime("%I:%M:%S %p")
    speak(f"The current time is {current_time}")


# Function to get current date and speak it
def get_date():
    year = datetime.datetime.now().year
    month = datetime.datetime.now().strftime("%B")
    day = datetime.datetime.now().day
    speak(f"Today is {month} {day}, {year}")


# Function to greet the user based on the time of day and stored context
def wish_me():
    global current_context
    hour = datetime.datetime.now().hour
    if 5 <= hour < 12:
        speak("Good morning!")
    elif 12 <= hour < 18:
        speak("Good afternoon!")
    elif 18 <= hour < 22:
        speak("Good evening!")
    else:
        speak("Hello!")

    # Retrieve context from long-term memory
    c.execute("SELECT value FROM memories WHERE context = 'current_context' AND key = 'context'")
    result = c.fetchone()
    if result:
        current_context = result[0]
    else:
        current_context = None

    if current_context:
        speak(f"Welcome back! How may I assist you {current_context}?")
    else:
        speak("At your service. How may I assist you today?")


# Function to recognize speech input from the user
def take_command():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        recognizer.pause_threshold = 1
        audio = recognizer.listen(source)

    try:
        print("Recognizing...")
        query = recognizer.recognize_google(audio, language='en-in').lower()
        print(f"User said: {query}")
    except sr.UnknownValueError:
        print("Sorry, I didn't catch that. Please say it again.")
        speak("Sorry, I didn't catch that. Please say it again.")
        return "None"
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        speak("Sorry, I am currently unable to process your request.")
        return "None"

    return query


# Function to open applications based on user input
def open_application(query):
    application_name = query.replace("open ", "").strip().lower()
    application_found = False

    common_directories = [
        "C:\Program Files",
        "C:\Program Files (x86)",
        "C:\\Users\\{your_username}\\AppData\\Local\\Programs\\"
    ]

    for directory in common_directories:
        for root, dirs, files in os.walk(directory):
            for file in files:
                if application_name in file.lower() and file.endswith('.exe'):
                    try:
                        os.startfile(os.path.join(root, file))
                        speak(f"Opening {application_name}")
                        log_activity(f"Opened {application_name}")
                        application_found = True
                        break
                    except Exception as e:
                        print(e)
                        continue

            if application_found:
                break

        if application_found:
            break

    if not application_found:
        speak(f"Sorry, I couldn't find {application_name} on your computer.")
        log_activity(f"Failed to open {application_name}")


# Function to search and download applications based on user input
def search_and_download(query):
    try:
        query = query.replace("download ", "")
        query = re.sub(r'\s+', '+', query)
        url = f"https://www.google.com/search?q={query}+download+link"

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        res = requests.get(url, headers=headers)
        res.raise_for_status()

        soup = BeautifulSoup(res.text, 'html.parser')
        links = soup.find_all('a')

        for link in links:
            href = link.get('href')
            if href and (href.startswith('http://') or href.startswith('https://')):
                webbrowser.open(href)
                speak(f"Downloading {query} from {href}. Please check your browser for download progress.")
                log_activity(f"Downloaded {query}")
                return

        speak(f"Sorry, I couldn't find a download link for {query}. Please try again later.")
    except Exception as e:
        print(e)
        speak("Sorry, I encountered an error while processing your request. Please try again later.")


# Function to run commands with administrator privileges
def run_as_admin(query):
    try:
        subprocess.run(query, shell=True, check=True)
        speak(f"Command executed with administrator privileges: {query}")
        log_activity(f"Executed command with admin privileges: {query}")
    except subprocess.CalledProcessError as e:
        print(f"Error executing command with admin privileges: {e}")
        speak("Sorry, there was an error executing the command.")


# Function to log activities to SQLite database
def log_activity(activity):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO activities (timestamp, activity) VALUES (?, ?)", (timestamp, activity))
    conn.commit()


# Function to store memories in SQLite database
def store_memory(context, key, value):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("INSERT INTO memories (context, key, value, timestamp) VALUES (?, ?, ?, ?)",
              (context, key, value, timestamp))
    conn.commit()

    if key == 'context':
        global current_context
        current_context = value


# Function to delete memories from SQLite database
def forget_memory(context, key=None):
    if key:
        c.execute("DELETE FROM memories WHERE context = ? AND key = ?", (context, key))
    else:
        c.execute("DELETE FROM memories WHERE context = ?", (context,))
    conn.commit()


def search_website(query):
    try:
        search_url = f"https://www.google.com/search?q={query}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(search_url, headers=headers)
        response.raise_for_status()

        # Parse the HTML response to extract search results
        soup = BeautifulSoup(response.content, 'html.parser')
        search_results = soup.find_all('div', class_='BVG0Nb')

        if search_results:
            # Extract and speak the first search result title
            result_title = search_results[0].text
            speak(f"Here is the top result: {result_title}")
        else:
            speak("Sorry, I couldn't find any results for that query.")
    except Exception as e:
        print(f"Error searching website: {e}")
        speak("Sorry, I encountered an error while searching the website.")


# Function to generate a response using GPT-2 model
def generate_response(user_input, context=None):
    global model, tokenizer, max_length, device

    input_text = user_input
    if context:
        input_text = f"{context} {user_input}"

    # Tokenize input text
    input_ids = tokenizer.encode(input_text, return_tensors='pt').to(device)

    if input_ids is None:
        print("Error: tokenizer.encode() returned None.")
        return "I'm sorry, I didn't understand that."

    with torch.no_grad():
        # Generate response
        output = model.generate(input_ids,
                                max_length=max_length,
                                num_return_sequences=1,
                                pad_token_id=tokenizer.eos_token_id,
                                attention_mask=input_ids.ne(tokenizer.pad_token_id).to(device))

    response = tokenizer.decode(output[0], skip_special_tokens=True)

    # Handle special cases
    if 'exit chat mode' in response.lower():
        return "exit chat mode"

    return response

# Function to enter chat mode for interactive conversation
def chat_mode():
    global current_context

    if current_context:
        speak(f"Entering chat mode under {current_context}. How may I assist you?")
    else:
        speak("Entering chat mode. How may I assist you?")

    while True:
        user_input = take_command().lower()

        if 'exit' in user_input:
            speak("Exiting chat mode.")
            forget_memory('current_context')
            break

        response = generate_response(user_input, context=current_context)
        speak(response)

# Function to get news headlines
def get_news_headlines():
    try:
        url = 'https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en'
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'xml')

        items = soup.findAll('item', limit=5)
        headlines = [item.title.text for item in items]

        return headlines
    except Exception as e:
        print(f"Error fetching news headlines: {e}")
        return None

# Function to get the weather forecast
def get_weather_forecast():
    try:
        url = 'https://www.weather.com/weather/today/l/USNY0996:1:US'
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.content, 'html.parser')

        temperature = soup.find(class_='CurrentConditions--tempValue--3KcTQ').get_text()
        description = soup.find(class_='CurrentConditions--phraseValue--2xXSr').get_text()

        return f"The current temperature is {temperature} and {description}."
    except Exception as e:
        print(f"Error fetching weather forecast: {e}")
        return None

# Function to send email
def send_email(recipient_email, subject, message):
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login('your_email@gmail.com', 'your_password')
        server.sendmail('your_email@gmail.com', recipient_email, f"Subject: {subject}\n\n{message}")
        server.quit()
        speak("Email sent successfully.")
    except Exception as e:
        print(f"Error sending email: {e}")
        speak("Sorry, I encountered an error while sending the email.")

# Function to tell a joke
def tell_joke():
    joke = pyjokes.get_joke()
    speak(joke)

# Function to get information from Wikipedia
def get_wikipedia_info(query):
    try:
        result = wikipedia.summary(query, sentences=2)
        speak("According to Wikipedia:")
        speak(result)
    except wikipedia.exceptions.PageError:
        speak("Sorry, I couldn't find any information on that topic.")
    except wikipedia.exceptions.DisambiguationError:
        speak("There are multiple matches for that topic. Please be more specific.")

# Function to get a daily briefing
def get_daily_briefing():
    speak("Fetching today's news headlines...")
    headlines = get_news_headlines()
    if headlines:
        speak("Here are the latest news headlines:")
        for headline in headlines:
            speak(headline)
    else:
        speak("Sorry, I couldn't fetch the latest news headlines.")

    speak("Fetching today's weather forecast...")
    weather_info = get_weather_forecast()
    if weather_info:
        speak(weather_info)
    else:
        speak("Sorry, I couldn't fetch the weather forecast.")

# Function to interact with home automation systems
def home_automation(command):
    # Example: Control lights, temperature, security systems, etc.
    if 'lights' in command:
        speak("Turning on the lights.")
        # Code to control lights
    elif 'temperature' in command:
        speak("Setting the temperature to 22 degrees Celsius.")
        # Code to adjust temperature
    elif 'security' in command:
        speak("Activating security system.")
        # Code to activate security system
    else:
        speak("Sorry, I don't understand that command.")

# Function to perform mathematical calculations using Wolfram Alpha API
def calculate_math(expression):
    try:
        res = wolfram_alpha_client.query(expression)
        answer = next(res.results).text
        speak(f"The answer is {answer}")
    except Exception as e:
        print(f"Error calculating math expression: {e}")
        speak("Sorry, I couldn't perform the calculation.")

# Function to list files in a directory
def list_files(directory):
    try:
        files = os.listdir(directory)
        if files:
            speak(f"Here are the files in {directory}:")
            for file in files:
                speak(file)
        else:
            speak(f"No files found in {directory}")
    except Exception as e:
        print(f"Error listing files: {e}")
        speak("Sorry, I encountered an error while listing the files.")

# Function to open a file
def open_file(file_path):
    try:
        os.startfile(file_path)
        speak(f"Opening {file_path}")
    except Exception as e:
        print(f"Error opening file: {e}")
        speak(f"Sorry, I couldn't open {file_path}")

# Function to rename a file
def rename_file(old_name, new_name):
    try:
        os.rename(old_name, new_name)
        speak(f"File {old_name} renamed to {new_name}")
    except Exception as e:
        print(f"Error renaming file: {e}")
        speak(f"Sorry, I couldn't rename the file {old_name}")

# Function to delete a file
def delete_file(file_path):
    try:
        os.remove(file_path)
        speak(f"File {file_path} deleted")
    except Exception as e:
        print(f"Error deleting file: {e}")
        speak(f"Sorry, I couldn't delete the file {file_path}")


# Main function to execute the assistant
if __name__ == "__main__":
    initialize_database()
    wish_me()

    while True:
        query = take_command().lower()

        if 'time' in query:
            get_time()
        elif 'date' in query:
            get_date()
        elif 'open' in query:
            open_application(query)
        elif 'search' in query and 'download' in query:
            search_and_download(query)
        elif 'run as admin' in query:
            run_as_admin(query)
        elif 'search' in query and 'website' in query:
            search_query = query.replace('search', '').strip()
            search_website(search_query)
        elif 'news' in query:
            get_news_headlines()
        elif 'weather' in query:
            get_weather_forecast()
        elif 'home automation' in query:
            home_automation(query)
        elif 'calculate' in query or 'math' in query:
            expression = query.replace('calculate', '').replace('math', '').strip()
            calculate_math(expression)
        elif 'list files' in query:
            directory = 'C:\\Users\\your_username\\Documents'  # Replace with your directory path
            list_files(directory)
        elif 'open file' in query:
            file_path = query.replace('open file', '').strip()
            open_file(file_path)
        elif 'rename file' in query:
            # Example: "rename file old_name new_name"
            parts = query.split()
            if len(parts) >= 3:
                old_name = parts[2]
                new_name = parts[3]
                rename_file(old_name, new_name)
            else:
                speak("Please provide both old and new names for renaming.")
        elif 'delete file' in query:
            file_path = query.replace('delete file', '').strip()
            delete_file(file_path)
        elif 'exit' in query:
            speak("Exiting the program. Have a nice day!")
            break
        else:
            # Generate response using GPT-2 model or other methods
            response = generate_response(query, context=current_context)
            speak(response)

    conn.close()
