import base64
from rich import print
from rich import console
import httpx
from rich.prompt import Prompt
import os
from dotenv import load_dotenv

load_dotenv()
con = console.Console()

IS_READY = False
ENCODED_IMAGE = ""
IMAGE_MEDIA_TYPE = ""

def encode_file(file_path : str):
    con.log("We are now trying to encode the file")
    con.log(f"The file path given is {file_path}")
    global ENCODED_IMAGE, IMAGE_MEDIA_TYPE, IS_READY
    with open(file_path, "rb") as file :
        ENCODED_IMAGE = base64.b64encode(file.read()).decode("utf-8")
    if file_path.endswith(".png"):
        IMAGE_MEDIA_TYPE = "image/png"
    elif file_path.endswith(".jpg"):
        IMAGE_MEDIA_TYPE = "image/jpg"
    elif file_path.endswith(".jpeg"):
        IMAGE_MEDIA_TYPE = "image/jpeg"
    IS_READY = True
    con.print("We are ready for your question about the image")
    return True

def sendingToAi(user_query : str):
    global ENCODED_IMAGE, IMAGE_MEDIA_TYPE
    api_key = os.getenv("API_KEY")
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 1000,
        "messages": [{"role": "user", "content": [
            {
                "type" : "image", 
                "source" : {
                    "type" : "base64",
                    "media_type" : IMAGE_MEDIA_TYPE,
                    "data" : ENCODED_IMAGE
                }
            }, 
            {"type" : "text", "text" : user_query}
        ]}]
    }
    try : 
        with httpx.Client() as client:
            api_response = client.post("https://api.anthropic.com/v1/messages", headers = headers, json=payload)
            response_in_json = api_response.json()
            print(response_in_json)
    except httpx.HTTPError as err:
        print("Exception Caused For ", err)


def main():
    con.log("Starting the application")
    print("This application will take in a photo and then answer your questions based on the photo you gave it.")
    print("Please type in or past the photo path into the textfield")
    global IS_READY
    while True:
        try:
            input = Prompt.ask("")
            if input.strip() == "":
                continue
            if IS_READY:
                con.log("Sending the image information and the user query to the Ai for answers")
                sendingToAi(input)
                continue
            should_continue = encode_file(input)
            if not should_continue:
                break
        except KeyboardInterrupt:
            con.print("\nExiting the program. Goodbye!", style="bold red")
            break

if __name__ == "__main__":
    main()
