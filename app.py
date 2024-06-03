import os
import json
import PyPDF2
from langchain_community.embeddings import OllamaEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ChatMessageHistory, ConversationBufferMemory
from langchain_groq import ChatGroq
from dotenv import load_dotenv
from google.auth.transport.requests import Request
from youtube_transcript_api import YouTubeTranscriptApi
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageTemplate, Frame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor

# Loading environment variables from .env file
load_dotenv() 

# Set up authentication credentials
SCOPES = ['https://www.googleapis.com/auth/youtube.force-ssl']
creds = None
if os.path.exists('token.json'):
    with open('token.json', 'r') as token_file:
        info = json.load(token_file)
    creds = Credentials.from_authorized_user_info(info=info, scopes=SCOPES)

if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
        creds.refresh(Request())
    else:
        flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
        creds = flow.run_local_server(port=0)
    with open('token.json', 'w') as token_file:
        token_file.write(creds.to_json())

# Create YouTube API client
youtube = build('youtube', 'v3', credentials=creds)

# Function to generate PDF
def generate_pdf(video_title, transcript_text):
    # Clean up video title for PDF title
    cleaned_title = video_title.replace('_', ' ').title()

    # Create a PDF document
    pdf_filename = f"{video_title}_transcript.pdf"
    pdf = SimpleDocTemplate(pdf_filename, pagesize=A4, leftMargin=0.2*inch, rightMargin=0.2*inch, topMargin=0.4*inch, bottomMargin=0.2*inch)
    doc = SimpleDocTemplate(pdf_filename, pagesize=A4)


    # Set up custom styles
    styles = getSampleStyleSheet()
    style_heading = ParagraphStyle(
        name="HeadingStyle",
        fontName="Times-Bold",
        fontSize=28,
        leading=36,
        spaceBefore=32,
        spaceAfter=24,
        textColor=HexColor("#041f1e"),  # Dark blue color
    )
    style_body = ParagraphStyle(
        name="BodyStyle",
        fontName="Helvetica",
        fontSize=14,
        leading=20,
        spaceBefore=16,
        spaceAfter=16,
        textColor=HexColor("#000000"),  # Dark gray color
    )

    # Set up page templates with headers and footers
    header_style = ParagraphStyle(
        name="HeaderStyle",
        fontName="Helvetica-Bold",
        fontSize=14,
        textColor=HexColor("#2980b9"),  # Blue color
    )
    footer_style = ParagraphStyle(
        name="FooterStyle",
        fontName="Helvetica-Italic",
        fontSize=12,
        textColor=HexColor("#7f8c8d"),  # Gray color
    )

    def create_header(canvas, doc):
        canvas.saveState()
        header_text = "YouTube Transcript"
        header_paragraph = Paragraph(header_text, header_style)
        header_paragraph.wrapOn(canvas, doc.width, doc.topMargin)
        header_paragraph.drawOn(canvas, doc.leftMargin, doc.height + doc.topMargin - 0.2 * inch)
        canvas.restoreState()

    def create_footer(canvas, doc):
        canvas.saveState()
        footer_text = f"Page {doc.page} - {video_title}"
        footer_paragraph = Paragraph(footer_text, footer_style)
        footer_paragraph.wrapOn(canvas, doc.width, doc.bottomMargin)
        footer_paragraph.drawOn(canvas, doc.leftMargin, 0.2 * inch)
        canvas.restoreState()

    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
    template = PageTemplate(id="main", frames=frame, onPage=create_header, onPageEnd=create_footer)
    doc.addPageTemplates([template])

    # Create content
    content = []
    content.append(Paragraph(cleaned_title, style_heading))
    content.append(Spacer(1, 24))
    content.append(Paragraph(transcript_text, style_body))

    # Build PDF
    pdf.build(content)
    print(f"PDF saved as: {pdf_filename}")

# Function to initialize conversation chain with GROQ language model
groq_api_key = os.environ['GROQ_API_KEY']

# Initializing GROQ chat with provided API key, model name, and settings
llm_groq = ChatGroq(
            groq_api_key=groq_api_key, model_name="mixtral-8x7b-32768",
                         temperature=0.2)

# Function to handle chat interaction
async def chat_with_pdf(pdf_filename):
    # Read the PDF file
    pdf = PyPDF2.PdfReader(pdf_filename)
    pdf_text = ""
    for page in pdf.pages:
        pdf_text += page.extract_text()
        
    # Split the text into chunks
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1200, chunk_overlap=50)
    texts = text_splitter.split_text(pdf_text)

    # Create a metadata for each chunk
    metadatas = [{"source": f"{i}-pl"} for i in range(len(texts))]

    # Create a Chroma vector store
    embeddings = OllamaEmbeddings(model="nomic-embed-text")
    docsearch = Chroma.from_texts(texts, embeddings, metadatas=metadatas)

    
    # Initialize message history for conversation
    message_history = ChatMessageHistory()
    
    # Memory for conversational context
    memory = ConversationBufferMemory(
        memory_key="chat_history",
        output_key="answer",
        chat_memory=message_history,
        return_messages=True,
    )

    # Create a chain that uses the Chroma vector store
    chain = ConversationalRetrievalChain.from_llm(
        llm=llm_groq,
        chain_type="stuff",
        retriever=docsearch.as_retriever(),
        memory=memory,
        return_source_documents=True,
    )

    # Chat loop
    print(f"Chatting with PDF: {pdf_filename}")
    print("You can start typing your questions. Type 'exit' to quit.")
    while True:
        question = input("You: ")
        if question.lower() == 'exit':
            break
        
        # call the chain with user's message content
        res = await chain.ainvoke(question)
        answer = res["answer"]
        source_documents = res["source_documents"] 

        if source_documents:
            for source_idx, source_doc in enumerate(source_documents):
                print(f"Source {source_idx}: {source_doc.page_content}")
        else:
            print("No sources found")
        print("Bot:", answer)

# Main function
async def main():
    # Get the video link from the user
    video_link = input("Enter the YouTube video link: ")

    # Extract video ID from the link
    video_id = video_link.split("v=")[1]

    # Get transcript for the video ID
    transcript = YouTubeTranscriptApi.get_transcript(video_id)

    # Extract text from transcript
    transcript_text = "\n".join(segment['text'] for segment in transcript)

    # Get video title from YouTube Data API
    video_info = youtube.videos().list(
        part='snippet',
        id=video_id
    ).execute()['items'][0]['snippet']
    video_title = video_info['title']

    # Generate and save PDF
    generate_pdf(video_title, transcript_text)

    # Chat with the generated PDF
    await chat_with_pdf(f"{video_title}_transcript.pdf")

# Run the main function
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
