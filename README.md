Video Chat App
This application allows users to enter a video link and chat with the content of that video. A UI will be added shortly.

Steps to Run:
Obtain your client_secret.json from the Google Cloud Console with the YouTube Data v3 API enabled.
Paste the client_secret.json into the root directory of this project.
Install the required Python packages by running:
bash
Copy code
pip install -r requirements.txt
Run the following command to pull the necessary data for Ollama:
bash
Copy code
ollama pull nomic-embed-text
Start the application by running:
bash
Copy code
python app.py
Once the application is running, enter the video link when prompted.
Chat with the content of the video.
