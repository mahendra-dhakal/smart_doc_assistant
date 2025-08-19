# Smart Doc Assistant

A smart chatbot that can answer questions from your documents and help schedule appointments. Built with FastAPI, LangChain, and Google Gemini.

## What it does

- **Chat about documents**: Upload PDFs and ask questions like "What are your business hours?"
- **Book appointments**: Say "I want you to call me" and it'll collect your info through conversation
- **Smart date parsing**: Understands "next Monday", "tomorrow", etc.
- **Input validation**: Checks emails and phone numbers automatically

## Quick Setup

1. **Clone and setup:**
   ```bash
   git clone <repository-url>
   cd smart-doc-assistant
   uv sync
   ```

2. **Get a Google API key:**
   - Go to [ai.google.dev](https://ai.google.dev/)
   - Create an API key
   - Copy `.env.example` to `.env` and add your key:
   ```
   GOOGLE_API_KEY=your_key_here
   ```

3. **Start the server:**
   ```bash
   uv run -m api.main
   ```

4. **Try it out:**
   - Open http://localhost:8000/docs
   - Test all the features right in your browser!

## How to use it

### Upload documents
- Use the `/documents/upload` endpoint to upload PDFs
- The bot will remember everything from your documents

### Chat with it
1. Create a new session: `POST /chat/new-session`
2. Send messages: `POST /chat` with your question
3. Try asking: "What services do you offer?" or "I need you to call me"

### Book appointments
Just say "call me" or "book appointment" and the bot will:
- Ask for your name
- Get your email
- Ask for your phone number
- Find out when you want to be called
- Confirm everything with you

## Example conversation

```
You: "I want you to call me"
Bot: "I'd love to help you schedule a call! Could you please tell me your full name?"

You: "John Smith"
Bot: "Perfect! Nice to meet you, John Smith. Now, could you please share your email address?"

You: "john@email.com"
Bot: "Excellent! Now, what's the best phone number to reach you at?"

You: "+1-555-123-4567"
Bot: "Perfect! When would be the best time for us to call you?"

You: "next Monday"
Bot: "Let me confirm your information:
Name: John Smith
Email: john@email.com  
Phone: +1-555-123-4567
Preferred call date: 2025-08-25

Is this information correct? (yes/no)"
```

## What's inside

```
smart-doc-assistant/
├── api/                    # FastAPI server
├── chatbot/               # AI logic
├── documents/             # Your PDF files go here
└── requirements.txt       # Dependencies
```

## Key features

- **Sessions**: Multiple people can use it at the same time
- **Smart forms**: Remembers where you left off if something goes wrong
- **Date magic**: "next Friday" becomes "2025-08-22" automatically
- **Input checking**: Won't accept invalid emails or phone numbers
- **Document search**: Finds relevant info from your PDFs instantly

## API endpoints

The main ones you'll use:
- `POST /chat/new-session` - Start chatting
- `POST /chat` - Send a message
- `POST /documents/upload` - Add PDF files
- `GET /docs` - Interactive testing (this is the best part!)

## Tech stuff

Built with:
- **FastAPI** - Modern Python web framework
- **LangChain** - AI application framework  
- **Google Gemini** - Smart language model
- **FAISS** - Fast document search

## Troubleshooting

**Can't start the server?**
- Make sure you have `uv` installed (`pip install uv` or visit [docs.astral.sh/uv](https://docs.astral.sh/uv/))
- Run `uv sync` first to install dependencies
- Check that your API key is in the `.env` file

**Bot not finding documents?**
- Upload PDFs using the `/documents/upload` endpoint
- Make sure they're actual PDF files

**Appointment form acting weird?**
- Use the reset form endpoint: `POST /chat/session/{session_id}/reset-form`

