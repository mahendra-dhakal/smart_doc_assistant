from typing import Dict, Any, Optional, List
from datetime import datetime
from langchain.tools import BaseTool
from langchain.agents import initialize_agent, AgentType
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.schema import BaseMessage
from pydantic import BaseModel, Field
from typing import Type
import json


class BookingInput(BaseModel):
    booking_info: str = Field(description="JSON string containing appointment booking information with keys: name, email, phone, date")


class AvailabilityInput(BaseModel):
    date: str = Field(description="Date to check availability for in YYYY-MM-DD format")

from chatbot.forms.conversational_form import ConversationalForm
from chatbot.utils.date_parser import DateParser


class AppointmentBookingTool(BaseTool):
    """Tool for booking appointments"""
    name: str = "book_appointment"
    description: str = """Books an appointment for a user. Input should be a JSON string with keys: name, email, phone, date. 
    Example: '{"name": "John Doe", "email": "john@example.com", "phone": "123-456-7890", "date": "2024-01-15"}'"""
    args_schema: Type[BaseModel] = BookingInput
    
    def _run(self, booking_info: str) -> str:
        """Execute the appointment booking"""
        try:
            # Parse the JSON input
            info = json.loads(booking_info)
            name = info.get("name")
            email = info.get("email") 
            phone = info.get("phone")
            date = info.get("date")
            
            if not all([name, email, phone, date]):
                return "Error: Missing required information. Please provide name, email, phone, and date."
            
            # In a real application, this would integrate with a calendar system
            # For now, we'll simulate the booking
            appointment_id = f"APT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
            
            booking_details = {
                "appointment_id": appointment_id,
                "name": name,
                "email": email,
                "phone": phone,
                "date": date,
                "status": "confirmed",
                "created_at": datetime.now().isoformat()
            }
            
            # Here you would typically save to a database
            print(f"Appointment booked: {booking_details}")
            
            return f"Appointment successfully booked! Your appointment ID is {appointment_id} for {date}."
        
        except json.JSONDecodeError:
            return "Error: Invalid input format. Please provide booking information as JSON."
        except Exception as e:
            return f"Error booking appointment: {str(e)}"
    
    async def _arun(self, *args, **kwargs) -> str:
        return self._run(*args, **kwargs)


class CheckAvailabilityTool(BaseTool):
    """Tool for checking appointment availability"""
    name: str = "check_availability"
    description: str = "Checks availability for a given date"
    args_schema: Type[BaseModel] = AvailabilityInput
    
    def _run(self, date: str) -> str:
        """Check availability for a specific date"""
        # In a real application, this would check against a calendar system
        # For now, we'll simulate availability checking
        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d")
            weekday = parsed_date.strftime("%A")
            
            # Simple availability logic (avoid weekends for demo)
            if weekday in ["Saturday", "Sunday"]:
                return f"Sorry, we're not available on {weekday}s. Please choose a weekday."
            else:
                available_times = ["09:00 AM", "11:00 AM", "02:00 PM", "04:00 PM"]
                return f"Available times for {date} ({weekday}): {', '.join(available_times)}"
        
        except ValueError:
            return "Invalid date format. Please provide date in YYYY-MM-DD format."
    
    async def _arun(self, date: str) -> str:
        return self._run(date)


class AppointmentAgent:
    def __init__(self, api_key: str):
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.3
        )
        
        self.tools = [
            AppointmentBookingTool(),
            CheckAvailabilityTool()
        ]
        
        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.STRUCTURED_CHAT_ZERO_SHOT_REACT_DESCRIPTION,
            verbose=True,
            handle_parsing_errors=True
        )
        
        self.conversational_form = ConversationalForm()
    
    def should_trigger_form(self, user_message: str) -> bool:
        """Determine if user wants to book an appointment or be called"""
        trigger_phrases = [
            "call me", "contact me", "book appointment", "schedule call",
            "get in touch", "reach out", "phone me", "ring me",
            "set up meeting", "arrange call", "callback"
        ]
        
        user_message_lower = user_message.lower()
        return any(phrase in user_message_lower for phrase in trigger_phrases)
    
    def process_message(self, user_message: str) -> Dict[str, Any]:
        """Process user message and determine appropriate response"""
        
        # If form is active, handle form input
        if self.conversational_form.is_active():
            form_result = self.conversational_form.process_input(user_message)
            
            # If form is completed, book the appointment
            if form_result["completed"]:
                user_info = form_result["user_info"]
                booking_result = self._book_appointment(user_info)
                return {
                    "response": form_result["response"] + "\n\n" + booking_result,
                    "form_active": False,
                    "appointment_booked": True
                }
            
            return {
                "response": form_result["response"],
                "form_active": True,
                "form_state": form_result["state"],
                "appointment_booked": False
            }
        
        # Check if user wants to start the appointment booking process
        if self.should_trigger_form(user_message):
            response = self.conversational_form.start_form()
            return {
                "response": response,
                "form_active": True,
                "form_state": self.conversational_form.get_current_state(),
                "appointment_booked": False
            }
        
        # Handle other appointment-related queries using the agent
        if any(word in user_message.lower() for word in ["appointment", "available", "book", "schedule"]):
            try:
                # Extract date if mentioned in the message
                extracted_date = DateParser.extract_date_from_text(user_message)
                
                if extracted_date and "available" in user_message.lower():
                    # Check availability
                    availability_result = self.tools[1]._run(extracted_date)
                    return {
                        "response": availability_result,
                        "form_active": False,
                        "appointment_booked": False
                    }
                else:
                    # Use agent for general appointment queries
                    agent_response = self.agent.run(user_message)
                    return {
                        "response": agent_response,
                        "form_active": False,
                        "appointment_booked": False
                    }
            
            except Exception as e:
                return {
                    "response": f"I encountered an error: {str(e)}. Would you like me to help you book an appointment?",
                    "form_active": False,
                    "appointment_booked": False
                }
        
        return {
            "response": None,  # Indicates this agent doesn't handle this message
            "form_active": False,
            "appointment_booked": False
        }
    
    def _book_appointment(self, user_info: Dict[str, Any]) -> str:
        """Book appointment with collected user information"""
        try:
            booking_info = json.dumps({
                "name": user_info["name"],
                "email": user_info["email"],
                "phone": user_info["phone"],
                "date": user_info["preferred_date"]
            })
            booking_result = self.tools[0]._run(booking_info)
            self.conversational_form.reset_form()
            return booking_result
        
        except Exception as e:
            return f"Sorry, I encountered an error while booking your appointment: {str(e)}"
    
    def reset_form(self):
        """Reset the conversational form"""
        self.conversational_form.reset_form()
    
    def get_form_status(self) -> Dict[str, Any]:
        """Get current form status"""
        return {
            "active": self.conversational_form.is_active(),
            "completed": self.conversational_form.is_completed(),
            "state": self.conversational_form.get_current_state(),
            "collected_info": self.conversational_form.get_collected_info()
        }