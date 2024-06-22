import sounddevice as sd
import numpy as np
import speech_recognition as sr
import os
from dotenv import load_dotenv
from groq import Groq
from openai import OpenAI
from langchain.chains import LLMChain
from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    MessagesPlaceholder,
)
from langchain_core.messages import SystemMessage
from langchain.chains.conversation.memory import ConversationBufferWindowMemory
from langchain_groq import ChatGroq
from os import system

# Load the API key from the environment
load_dotenv()

def record_audio(duration=5, fs=44100):
    print("Recording...")
    recording = sd.rec(int(duration * fs), samplerate=fs, channels=1, dtype='int16')
    sd.wait()  # Wait until recording is finished
    print("Recording finished")
    return recording

def recognize_speech_from_audio(audio, fs=44100):
    recognizer = sr.Recognizer()
    audio_data = sr.AudioData(audio.tobytes(), fs, 2)
    try:
        text = recognizer.recognize_google(audio_data)
        print("Recognized Text:", text)
        return text
    except sr.UnknownValueError:
        print("Google Speech Recognition could not understand audio")
        return ""
    except sr.RequestError as e:
        print("Could not request results from Google Speech Recognition service; {0}".format(e))
        return ""

def chat_with_assistant():
    groq_api_key = os.environ['GROQ_KEY']
    openai_api_key = os.environ['OPENAI_KEY']
    model = 'llama3-8b-8192'

    client = OpenAI(api_key=openai_api_key)

    groq_chat = ChatGroq(
            groq_api_key=groq_api_key, 
            model_name=model
    )

    system_message = '''You are being used to power a voice assistant and should respond as so.
            As a voice assistant, use short sentences. '''
    system_message = system_message.replace('\n', '')

    conversational_memory_length = 5  # Number of previous messages the chatbot will remember during the conversation

    memory = ConversationBufferWindowMemory(k=conversational_memory_length, memory_key="chat_history", return_messages=True)

    while True:
        # Record user question
        audio = record_audio(duration=5, fs=44100)
        user_question = recognize_speech_from_audio(audio, fs=44100)
        
        if user_question:
            print("User:", user_question)
            # Construct a chat prompt template using various components
            prompt = ChatPromptTemplate.from_messages(
                [
                    SystemMessage(content=system_message),  # This is the persistent system prompt that is always included at the start of the chat.
                    MessagesPlaceholder(variable_name="chat_history"),  # This placeholder will be replaced by the actual chat history during the conversation. It helps in maintaining context.
                    HumanMessagePromptTemplate.from_template("{human_input}"),  # This template is where the user's current input will be injected into the prompt.
                ]
            )

            # Create a conversation chain using the LangChain LLM (Language Learning Model)
            conversation = LLMChain(
                llm=groq_chat,  # The Groq LangChain chat object initialized earlier.
                prompt=prompt,  # The constructed prompt template.
                verbose=False,  # TRUE Enables verbose output, which can be useful for debugging.
                memory=memory,  # The conversational memory object that stores and manages the conversation history.
            )

            # The chatbot's answer is generated by sending the full prompt to the Groq API.
            response = conversation.predict(human_input=user_question)
            print("Chatbot:", response)

            with client.audio.speech.with_streaming_response.create(
                model='tts-1',
                voice='alloy',
                input=response
            ) as speech_response:
                speech_response.stream_to_file("speech.mp3")
            
            system("afplay speech.mp3")

def main():
    wake_word = "hello"
    duration = 2  # seconds
    fs = 44100  # Sample rate

    while True:
        audio = record_audio(duration, fs)
        recognized_text = recognize_speech_from_audio(audio, fs)
        if wake_word.lower() in recognized_text.lower():
            print("Wake word detected!")
            chat_with_assistant()

if __name__ == "__main__":
    main()
