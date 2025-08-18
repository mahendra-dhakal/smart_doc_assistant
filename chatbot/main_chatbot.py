import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain.memory import ConversationBufferMemory

from chatbot.document_processor import DocumentProcessor
from chatbot.agents.appointment_agent import AppointmentAgent

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MainChatbot:
    def __init__(self, api_key: str, documents_path: str = "documents"):
        self.api_key = api_key
        self.documents_path = documents_path
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.7
        )
        
        # Initialize conversation memory
        self.memory = ConversationBufferMemory(
            return_messages=True,
            memory_key="chat_history"
        )
        
        # Initialize document processor
        self.document_processor = DocumentProcessor(api_key)
        self.vector_store = self.document_processor.process_documents(documents_path)
        
        # Initialize appointment agent
        self.appointment_agent = AppointmentAgent(api_key)
        
        # System prompt for the main chatbot
        self.system_prompt = """You are a knowledgeable and friendly AI assistant for our company. Your primary responsibilities are:

1. Document Knowledge: You have access to our company's documents and can answer questions about our services, policies, pricing, and procedures. Always cite sources when referencing specific information from documents.

2. Appointment Scheduling: When customers want to schedule calls or meetings, you collect their contact information through a conversational process. You're patient and helpful during this process.

3. General Support: You provide helpful information and assistance with general inquiries.

Communication Style:
- Be conversational and professional
- Ask clarifying questions when needed
- Provide complete and accurate information
- If you don't know something, say so honestly
- Always confirm important details with customers

Remember: You represent our company, so maintain a helpful and professional tone throughout all interactions."""
    
    def chat(self, user_message: str) -> Dict[str, Any]:
        """Main chat function that handles all user interactions"""
        
        # First, check if the appointment agent should handle this message
        appointment_response = self.appointment_agent.process_message(user_message)
        
        if appointment_response["response"] is not None:
            # Appointment agent handled the message
            self._add_to_memory(user_message, appointment_response["response"])
            return {
                "response": appointment_response["response"],
                "source": "appointment_agent",
                "form_active": appointment_response.get("form_active", False),
                "appointment_booked": appointment_response.get("appointment_booked", False)
            }
        
        # Check if this is a document-related query
        if self._is_document_query(user_message):
            return self._handle_document_query(user_message)
        
        # Handle general conversation
        return self._handle_general_query(user_message)
    
    def _is_document_query(self, message: str) -> bool:
        """Determine if the message is asking about documents"""
        document_keywords = [
            "document", "file", "pdf", "information", "details", "explain",
            "what is", "tell me about", "find", "search", "look up",
            "according to", "based on", "in the document"
        ]
        
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in document_keywords)
    
    def _handle_document_query(self, user_message: str) -> Dict[str, Any]:
        """Handle queries about documents using RAG"""
        try:
            # Search for relevant documents
            relevant_docs = self.document_processor.search_documents(user_message, k=4)
            
            if not relevant_docs or (len(relevant_docs) == 1 and "No documents loaded" in relevant_docs[0].page_content):
                response = "I don't have any documents loaded in my knowledge base yet. Please upload some documents first, or I can help you with general questions or appointment booking."
                self._add_to_memory(user_message, response)
                return {
                    "response": response,
                    "source": "document_processor",
                    "documents_found": False
                }
            
            # Create context from relevant documents
            context = "\n".join([doc.page_content for doc in relevant_docs])
            
            # Create prompt with context
            prompt = f"""Based on the following context from documents, answer the user's question. 
If the answer cannot be found in the context, say so clearly.

Context:
{context}

User Question: {user_message}

Answer:"""
            
            # Get response from LLM
            messages = [
                SystemMessage(content=self.system_prompt),
                HumanMessage(content=prompt)
            ]
            
            response = self.llm(messages)
            response_text = response.content
            
            # Add source information
            source_files = list(set([doc.metadata.get('source', 'Unknown') for doc in relevant_docs]))
            if source_files and source_files != ['Unknown']:
                response_text += f"\n\nSources: {', '.join(source_files)}"
            
            self._add_to_memory(user_message, response_text)
            
            return {
                "response": response_text,
                "source": "document_processor",
                "documents_found": True,
                "source_files": source_files
            }
        
        except Exception as e:
            error_response = f"I encountered an error while searching the documents: {str(e)}"
            self._add_to_memory(user_message, error_response)
            return {
                "response": error_response,
                "source": "document_processor",
                "error": True
            }
    
    def _handle_general_query(self, user_message: str) -> Dict[str, Any]:
        """Handle general conversation queries"""
        try:
            # Get conversation history
            chat_history = self.memory.chat_memory.messages
            
            # Create messages for the conversation
            messages = [SystemMessage(content=self.system_prompt)]
            messages.extend(chat_history)
            messages.append(HumanMessage(content=user_message))
            
            # Get response from LLM
            response = self.llm(messages)
            response_text = response.content
            
            self._add_to_memory(user_message, response_text)
            
            return {
                "response": response_text,
                "source": "general_conversation"
            }
        
        except Exception as e:
            error_response = f"I encountered an error: {str(e)}"
            self._add_to_memory(user_message, error_response)
            return {
                "response": error_response,
                "source": "general_conversation",
                "error": True
            }
    
    def _add_to_memory(self, user_message: str, ai_response: str):
        """Add conversation to memory"""
        self.memory.chat_memory.add_user_message(user_message)
        self.memory.chat_memory.add_ai_message(ai_response)
    
    def add_documents(self, documents_path: str) -> str:
        """Add new documents to the knowledge base"""
        try:
            # Reprocess documents
            self.vector_store = self.document_processor.process_documents(documents_path)
            return f"Successfully processed documents from {documents_path}"
        except Exception as e:
            return f"Error processing documents: {str(e)}"
    
    def clear_memory(self):
        """Clear conversation memory"""
        self.memory.clear()
    
    def get_conversation_history(self) -> list:
        """Get conversation history"""
        return self.memory.chat_memory.messages
    
    def reset_appointment_form(self):
        """Reset the appointment booking form"""
        self.appointment_agent.reset_form()
    
    def get_appointment_status(self) -> Dict[str, Any]:
        """Get current appointment booking status"""
        return self.appointment_agent.get_form_status()


def create_chatbot(api_key: Optional[str] = None, documents_path: str = "documents") -> MainChatbot:
    """Factory function to create a chatbot instance"""
    if not api_key:
        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")
        
        if not api_key:
            raise ValueError("GOOGLE_API_KEY not found. Please set it in your .env file or pass it as a parameter.")
    
    return MainChatbot(api_key, documents_path)