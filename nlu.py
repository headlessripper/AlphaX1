import wikipedia
import requests
from bs4 import BeautifulSoup
import pyttsx3
import logging
import spacy
from transformers import pipeline
from nltk.sentiment import SentimentIntensityAnalyzer
import nltk
import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Download the required NLTK data
nltk.download('vader_lexicon')
nltk.download('punkt')  # Tokenizer models
nltk.download('stopwords')  # Common stopwords
nltk.download('wordnet')  # WordNet lexicon

class ExtendedNLU:
    def __init__(self, google_api_key, search_engine_id):
        self.google_api_key = google_api_key
        self.search_engine_id = search_engine_id
        self.speech_engine = pyttsx3.init()
        self.memory = {}
        self.context = {}
        self.logger = logging.getLogger(__name__)
        logging.basicConfig(level=logging.INFO)
        self.nlp = spacy.load("en_core_web_sm")
        self.text_generator = pipeline("text-generation", model="gpt2")
        self.sia = SentimentIntensityAnalyzer()

    def talk(self, text):
        """Convert text to speech and output."""
        self.speech_engine.say(text)
        self.speech_engine.runAndWait()

    def search_wikipedia(self, query):
        """Search Wikipedia for a summary of the query."""
        try:
            summary = wikipedia.summary(query, sentences=1)
            return summary
        except wikipedia.exceptions.DisambiguationError as e:
            options = ', '.join(e.options[:5])
            return f"There are several meanings for '{query}', could you be more specific? Here are some options: {options}."
        except wikipedia.exceptions.PageError:
            return f"I couldn't find anything on Wikipedia for '{query}'. Could you try rephrasing your request?"

    def search_web(self, query):
        """Perform a web search using Google Custom Search API and provide a detailed response."""
        url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={self.google_api_key}&cx={self.search_engine_id}"
        try:
            response = requests.get(url).json()
            items = response.get('items', [])

            if not items:
                return "I couldn't find any relevant information on the web. Maybe try rephrasing your query.", []

            # Extract top results
            results = []
            for item in items[:5]:  # Limit to top 5 results
                title = item.get('title', 'No title available')
                snippet = item.get('snippet', 'No snippet available')
                results.append({
                    'title': title,
                    'snippet': snippet
                })

            # Construct a detailed response
            detailed_response = "Here are some search results I found:\n\n"
            detailed_response += "\n\n".join(f"{result['title']}: {result['snippet']}" for result in results)
            return detailed_response, results

        except requests.RequestException as e:
            self.logger.error(f"Web search error: {e}")
            return "There was an error while searching the web. Please try again later.", []

    def scrape_web(self, url):
        """Scrape content from a web page."""
        try:
            response = requests.get(url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            paragraphs = soup.find_all('p')
            content = ' '.join([para.get_text() for para in paragraphs[:3]])
            return content
        except requests.RequestException as e:
            self.logger.error(f"Web scraping error: {e}")
            return f"Couldn't scrape the content from the website. Error: {e}"

    def extract_human_responses(self, snippet):
        """Extract human-like responses from a text snippet."""
        doc = self.nlp(snippet)
        responses = [sent.text for sent in doc.sents if "reply" in sent.text.lower() or "respond" in sent.text.lower()]
        return responses[0] if responses else "Sorry, I couldn't find a suitable response for that."

    def handle_conversation(self, text):
        """Handle predefined conversational responses."""
        text_lower = text.lower()
        responses = {
            "how are you": "I'm doing great sir! How about you?",
            "im fine thanks for asking": "It is my duty to serve you!",
            "did you get enough sleep": "I don't sleep, but I appreciate the concern! How about you? Did you get enough rest?",
            "hello": "Hello! How can I assist you today?",
            "hi": "Hi there! What can I do for you today?",
            "thank you": "You're welcome! If you have any more questions, feel free to ask.",
            "bye": "Goodbye! Have a great day!",
            "nice": "I'm glad you think so! If you need anything else, just let me know.",
            "wow": "I'm glad you're impressed! Let me know if there's anything else you'd like to know."
        }
        for keyword, response in responses.items():
            if keyword in text_lower:
                self.context['last_interaction'] = keyword
                return response
        return None

    def store_memory(self, key, value):
        """Store information in memory."""
        self.memory[key] = value

    def retrieve_memory(self, key):
        """Retrieve information from memory."""
        return self.memory.get(key, None)

    def update_context(self, key, value):
        """Update conversational context."""
        self.context[key] = value

    def filter_information(self, query, information):
        """Filter information based on context."""
        context_keywords = {
            "well-being": ["how are you", "are you ok", "how do you feel", "did you get enough sleep"],
            "greeting": ["hello", "hi"],
            "thanks": ["thank you", "thanks"],
            "appreciation": ["nice", "wow"]
        }

        for key, keywords in context_keywords.items():
            if any(keyword in query.lower() for keyword in keywords):
                if key == "well-being":
                    return "I'm doing fine, thank you for asking! How can I assist you further?"
                elif key == "greeting":
                    return "Hello! How can I help you today?"
                elif key == "thanks":
                    return "You're welcome! If you need more help, just ask."
                elif key == "appreciation":
                    return "I'm glad you think so! If you need anything else, just let me know."

        return information

    def generate_response(self, prompt):
        """Generate a response using a text generation model."""
        try:
            response = self.text_generator(
                prompt, 
                max_length=150,  # Increased length to handle longer inputs
                num_return_sequences=1, 
                truncation=True,
                pad_token_id=self.text_generator.tokenizer.eos_token_id,
                max_new_tokens=100
            )
            return response[0]['generated_text'].strip()
        except Exception as e:
            self.logger.error(f"Text generation error: {e}")
            return "I encountered an error generating a response. Please try again later."

    def analyze_sentiment(self, text):
        """Analyze the sentiment of the text."""
        sentiment = self.sia.polarity_scores(text)
        if sentiment['compound'] >= 0.05:
            return "positive"
        elif sentiment['compound'] <= -0.05:
            return "negative"
        else:
            return "neutral"

    def get_response(self, text):
        """Get a response based on the input text."""
        # Check for conversational responses first
        conversational_response = self.handle_conversation(text)
        if conversational_response:
            self.talk(conversational_response)
            return conversational_response

        # Retrieve from memory if applicable
        memory_response = self.retrieve_memory(text)
        if memory_response:
            self.talk(memory_response)
            return memory_response

        # Perform web search and get detailed results
        web_response, web_results = self.search_web(text)
        if web_results:
            self.talk(web_response)
            return web_response

        # Perform information retrieval from Wikipedia
        wiki_summary = self.search_wikipedia(text)
        
        # Perform web scraping if applicable
        scrape_content = self.scrape_web(text) if 'http' in text else None

        # Combine the information in a conversational manner
        combined_response = "Here's what I found for you:"

        if wiki_summary:
            combined_response += f"\n\nFrom Wikipedia: {wiki_summary}"
        if web_results:
            combined_response += "\n\nHere are some search results:\n" + "\n".join(
                [f"{result['title']}: {result['snippet']}" for result in web_results]
            )
        if scrape_content:
            combined_response += f"\n\nScraped Content: {scrape_content}"

        if not (wiki_summary or web_results or scrape_content):
            combined_response = "I couldn't find any useful information. Can you please provide more details or try rephrasing your query?"

        # Filter the response based on the context
        filtered_response = self.filter_information(text, combined_response)
        self.store_memory(text, filtered_response)  # Store the response in memory
        self.update_context('last_query', text)  # Update context with the latest query
        sentiment = self.analyze_sentiment(filtered_response)
        advanced_response = self.generate_response(f"User query: {text}. Sentiment: {sentiment}. Response: {filtered_response}")
        self.talk(advanced_response)
        return advanced_response

    def process_input(self, user_input):
        """Process user input and generate a response."""
        response = self.get_response(user_input)
        return response
