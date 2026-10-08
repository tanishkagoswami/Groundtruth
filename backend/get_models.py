import os
from groq import Groq
from dotenv import load_dotenv

# Load the .env file
load_dotenv()

# Initialize the Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def check_models():
    try:
        print("Fetching allowed models from Groq API...\n")
        models = client.models.list()
        
        for model in models.data:
            print(f"- {model.id}")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_models()