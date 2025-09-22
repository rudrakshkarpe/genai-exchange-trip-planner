import base64
import io
from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn
from google.cloud import texttospeech, speech
from vertexai import agent_engines
from typing import Any, AsyncIterable
from sub_agents.agent_host.agent import HostAgent
from api_schema import TripChatSchema

# --- FastAPI App Initialization ---
app = FastAPI(
    title="Chat API with Text and Speech Processing",
    description="An API that accepts text or audio, processes it, and returns text and speech.",
    version="1.0.0",
)

# --- Agent Instance ---
host_agent_instance: HostAgent | None = None

@app.on_event("startup")
async def startup_event():
    """Initializes the HostAgent when the application starts."""
    global host_agent_instance
    # These URLs are from your agent.py file
    agent_urls = [
            "https://inspiraiton-agent-683449264474.europe-west1.run.app", # Inspiration Agent
            "https://planning-agent-683449264474.europe-west1.run.app", # Planning Agent
            #"http://localhost:8001",  # Inspiration Agent
            "http://localhost:8002",  # Planning Agent
            # "http://localhost:8003",  # Booking Agent
            #"http://localhost:8004",  # Pre-Trip Agent
            #"http://localhost:8005",  # In-Trip Agent
            #"http://localhost:8006",  # Post-Trip Agent
        ]
    print("Initializing HostAgent...")
    host_agent_instance = await HostAgent.create(remote_agent_addresses=agent_urls)
    print("HostAgent initialized.")

# --- Pydantic Models for Response ---
class ChatResponse(BaseModel):
    text_response: str
    audio_response_base64: str

# --- Placeholder Functions for Gemini/Vertex AI ---

async def recognize_speech_to_text(audio_bytes: bytes) -> str:
    """
    Simulates a call to the Gemini/Vertex AI Speech-to-Text API.
    In a real implementation, you would use the Google Cloud client library.
    """
    print("--- Sending audio to Gemini STT (Simulated) ---")
    # This is a placeholder. A real implementation would look like this:
    #    
    client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=16000,
        language_code="en-US",
    )
    response = client.recognize(config=config, audio=audio)
    if not response.results:
        raise HTTPException(status_code=400, detail="Could not transcribe audio.")
    return response.results[0].alternatives[0].transcript


async def synthesize_text_to_speech(text: str) -> bytes:
    """
    Simulates a call to the Gemini/Vertex AI Text-to-Speech API.
    In a real implementation, you would use the Google Cloud client library.
    """
    print(f"--- Sending text to Gemini TTS (Simulated): '{text}' ---")
    # This is a placeholder. A real implementation would look like this:
    #
    
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    return response.audio_content


# --- External API Call Function ---

@app.post("/api/chat_endpoint")
async def chat_endpoint(request: TripChatSchema):
    """
    This endpoint handles both text and audio chat requests.

    - **To send text:** Use a form field named `text`.
    - **To send audio:** Upload a file to a form field named `audio_file`.

    The endpoint processes the input, calls an external API, and returns
    both a text response and a synthesized audio response.
    """
    # text = "whats weather in delhi today"
    input_text = ""

    # 1. Determine request type and get input text
    requests = request.dict()
    text = requests["text"]
    audio_file = requests["audio_file"]
    image = requests["image"]
    session_id = requests["session_id"]

    if audio_file:
        print("--- Received audio file ---")
        if not audio_file.content_type.startswith("audio/"):
            raise HTTPException(status_code=400, detail="Invalid file type. Please upload an audio file.")
        audio_bytes = await audio_file.read()
        try:
            input_text = await recognize_speech_to_text(audio_bytes)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Speech-to-Text processing failed: {e}")
    elif image and text.strip():
        # Encode the bytes to a base64 string

        base64_image = base64.b64encode(image).decode('utf-8')
        content_dict = {

        "role": "user",

        "parts": [

            {"text": text},

            {

                "inline_data": {

                    "mime_type": "image/jpeg",

                    "data": base64_image

                }

            }

        ]

        }
        input_text = content_dict
    elif image:
        raise HTTPException(status_code=422, detail=f"Please provide text with the image")
    elif text and not image: # if text
        print("--- Received text input ---",text)
        input_text = text
    else:
        pass
    # 2. Forward text to the external API
    if not host_agent_instance:
        raise HTTPException(status_code=503, detail="Agent is not initialized.")

    final_response = ""
    async for event in host_agent_instance.stream(query=input_text, session_id=session_id):
        print("OUTPUT EVENT----",event)
        if event.get("is_task_complete"):
            final_response = event.get("content", "")
            break  # Exit after getting the final response

    # 3. Pass the response to the TTS model
    try:
        #final_audio_bytes = await synthesize_text_to_speech(final_response)
        final_audio_bytes = ""
        print(final_response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Text-to-Speech processing failed: {e}")

    # 4. Prepare and return the final response
    # We can return the audio in two ways:
    # a) As a base64 string within a JSON object for clients that prefer it.
    # b) As a direct audio stream for browsers or clients that can play it.

    # For this example, we'll return a JSON response with the base64 audio
    # and also make the streaming audio available if requested via headers.
    # A more advanced implementation could use the 'Accept' header to decide.

    audio_base64 = ""#base64.b64encode(final_audio_bytes).decode('utf-8')

    response_data = ChatResponse(
        text_response=final_response,
        audio_response_base64=audio_base64
    )

    # You could also return a streaming response directly like this:
    # return StreamingResponse(io.BytesIO(final_audio_bytes), media_type="audio/mpeg")

    return JSONResponse(content=response_data.dict())


# --- Root endpoint for basic health check ---
@app.get("/")
def read_root():
    return {"message": "Chat API is running. Go to /docs for API documentation."}


# --- To run the app ---
# Command: uvicorn main:app --reload
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)