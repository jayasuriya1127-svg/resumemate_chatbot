"""
app.py

Flask backend for the ResumeMate chatbot.
Serves the chat UI and proxies chat messages to the Gemini API,
using the system prompt defined in chatbot_config.py.
"""

import os

from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify
from google import genai
from google.genai import types

from chatbot_config import SYSTEM_PROMPT

# Load variables from .env into the environment
load_dotenv()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")

if not GEMINI_API_KEY:
    raise RuntimeError(
        "GEMINI_API_KEY is not set. Please add it to your .env file."
    )

client = genai.Client(api_key=GEMINI_API_KEY)

app = Flask(__name__)


@app.route("/")
def index():
    """Render the chat UI."""
    return render_template("index.html")


@app.route("/api/chat", methods=["POST"])
def chat():
    """
    Receive a user message (and optional prior conversation history),
    send it to Gemini along with the fixed system prompt, and return
    the model's reply as JSON.
    """
    data = request.get_json(silent=True) or {}
    user_message = (data.get("message") or "").strip()
    history = data.get("history") or []  # list of {role, text}

    if not user_message:
        return jsonify({"error": "Message cannot be empty."}), 400

    # Build the conversation contents for the Gemini API.
    contents = []
    for turn in history:
        role = "model" if turn.get("role") == "bot" else "user"
        text = turn.get("text", "")
        if text:
            contents.append(
                types.Content(role=role, parts=[types.Part.from_text(text=text)])
            )
    contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=user_message)])
    )

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
            ),
        )
        reply_text = response.text or "Sorry, I couldn't generate a response."
    except Exception as exc:  # noqa: BLE001
        return jsonify({"error": f"Gemini API error: {exc}"}), 500

    return jsonify({"reply": reply_text})


if __name__ == "__main__":
    app.run(debug=True)
