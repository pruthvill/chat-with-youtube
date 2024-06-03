

**Chat with Youtube**

This application allows users to enter a video link and chat with the content of that video. A UI will be added shortly.

**Steps to Run:**

1. Obtain your `client_secret.json` from the Google Cloud Console with the YouTube Data v3 API enabled.
2. Paste the `client_secret.json` into the root directory of this project.
3. Install the required Python packages by running:

```bash
pip install -r requirements.txt
```

4. Run the following command to pull the necessary data for Ollama:

```bash
ollama pull nomic-embed-text
```

5. Start the application by running:

```bash
python app.py
```

6. Once the application is running, enter the video link when prompted.
7. Chat with the content of the video.