import base64
from rich import print
from rich import console
import httpx
from rich.prompt import Prompt
import os
from dotenv import load_dotenv

load_dotenv()
con = console.Console()

def encode_file(file_path : str):
    with open(file_path, "rb") as file : 
        encoded_image = base64.b64encode(file.read().decode("utf-8"))
    if file_path.endswith(".png"):
        image_media_type = "image/png"
    elif file_path.endswith(".jpg"):
        image_media_type = "image/jpg"
    elif file_path.endswith(".jpeg"):
        image_media_type = "image/jpeg"
    return encoded_image, image_media_type

def sendingToAi(user_query : str, encoded_data, image_media_type):
    api_key = os.getenv("API_KEY")
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 500,
        "messages": [{"role": "user", "content": [
            {
                "type" : "image", 
                "source" : {
                    "type" : "base64",
                    "media_type" : image_media_type,
                    "data" : encoded_data
                }
            }, 
            {"type" : "text", "text" : user_query}
        ]}]
    }
    try : 
        with httpx.Client as client:
            api_response = client.post("https://api.anthropic.com/v1/messages", headers = headers, payload=payload)
            response_in_json = api_response.json()
    except httpx.HTTPError as err:
        print("Exception Caused For ", err)


def main():
    con.log("Starting the application")
    print("This application will take in a photo and then answer your questions based on the photo you gave it.")
    print("Please type in or past the photo path into the textfield")
    while True:
        input = Prompt.ask("")

if __name__ == "__main__":
    main()
