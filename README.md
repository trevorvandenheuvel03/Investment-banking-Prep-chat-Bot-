# Investment-banking-Prep-chat-Bot-
Help students prep for investment banking interviews

Run locally
-----------

1.  Export your OpenAI key:

        export OPENAI_API_KEY=sk-...

2.  Install deps in a fresh venv:

        pip install -r requirements.txt

3.  Launch the server:

        uvicorn main:app --reload

4.  Open http://127.0.0.1:8000 in a browser and start practising.

Stack
-----

* **FastAPI + WebSockets** for backend and real‑time messaging  
* **OpenAI ChatCompletion** for scoring answers  
* **Jinja2** template serving one HTML page  
* **Vanilla JS** for socket logic, timer, and DOM updates  
* **No database** — session state lives in memory per WebSocket connection


fastapi
uvicorn
jinja2
python-mimeparse
openai
