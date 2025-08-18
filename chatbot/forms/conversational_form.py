from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel
from chatbot.utils.validators import InputValidator, ValidationError
from chatbot.utils.date_parser import DateParser


class FormState(Enum):
    INACTIVE = "inactive"
    COLLECTING_NAME = "collecting_name"
    COLLECTING_EMAIL = "collecting_email"
    COLLECTING_PHONE = "collecting_phone"
    COLLECTING_DATE = "collecting_date"
    CONFIRMING_INFO = "confirming_info"
    COMPLETED = "completed"


class UserInfo(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    preferred_date: Optional[str] = None


class ConversationalForm:
    def __init__(self):
        self.state = FormState.INACTIVE
        self.user_info = UserInfo()
        self.retry_count = 0
        self.max_retries = 3
    
    def start_form(self) -> str:
        """Start the conversational form"""
        self.state = FormState.COLLECTING_NAME
        self.user_info = UserInfo()
        self.retry_count = 0
        return "I'd love to help you schedule a call! To get started, I'll need to collect a few details from you.\n\nCould you please tell me your full name?"
    
    def process_input(self, user_input: str) -> Dict[str, Any]:
        """Process user input based on current form state"""
        response = ""
        completed = False
        
        try:
            if self.state == FormState.COLLECTING_NAME:
                response = self._handle_name_input(user_input)
            elif self.state == FormState.COLLECTING_EMAIL:
                response = self._handle_email_input(user_input)
            elif self.state == FormState.COLLECTING_PHONE:
                response = self._handle_phone_input(user_input)
            elif self.state == FormState.COLLECTING_DATE:
                response = self._handle_date_input(user_input)
            elif self.state == FormState.CONFIRMING_INFO:
                response = self._handle_confirmation(user_input)
            elif self.state == FormState.COMPLETED:
                completed = True
                response = "Your information has been recorded. We'll contact you soon!"
            
            self.retry_count = 0  # Reset retry count on successful input
            
        except ValidationError as e:
            self.retry_count += 1
            if self.retry_count >= self.max_retries:
                response = "I'm having trouble with this information. Let me restart the form."
                self.reset_form()
            else:
                response = f"{str(e)} Please try again."
        
        return {
            "response": response,
            "completed": completed,
            "state": self.state.value,
            "user_info": self.user_info.dict()
        }
    
    def _handle_name_input(self, user_input: str) -> str:
        """Handle name collection"""
        validated_name = InputValidator.validate_name(user_input)
        self.user_info.name = validated_name
        self.state = FormState.COLLECTING_EMAIL
        return f"Perfect! Nice to meet you, {validated_name}. Now, could you please share your email address so we can send you a confirmation?"
    
    def _handle_email_input(self, user_input: str) -> str:
        """Handle email collection"""
        validated_email = InputValidator.validate_email(user_input)
        self.user_info.email = validated_email
        self.state = FormState.COLLECTING_PHONE
        return "Excellent! I've got your email. Now, what's the best phone number to reach you at?"
    
    def _handle_phone_input(self, user_input: str) -> str:
        """Handle phone collection"""
        validated_phone = InputValidator.validate_phone(user_input)
        self.user_info.phone = validated_phone
        self.state = FormState.COLLECTING_DATE
        return "Perfect! I've got your contact details. When would be the best time for us to call you? You can say something like 'tomorrow afternoon', 'next Monday', or give me a specific date that works for you."
    
    def _handle_date_input(self, user_input: str) -> str:
        """Handle date collection"""
        parsed_date = DateParser.extract_date_from_text(user_input)
        
        if not parsed_date:
            raise ValidationError("I couldn't understand that date format.")
        
        if not DateParser.validate_future_date(parsed_date):
            raise ValidationError("Please provide a future date.")
        
        self.user_info.preferred_date = parsed_date
        self.state = FormState.CONFIRMING_INFO
        
        return self._generate_confirmation_message()
    
    def _handle_confirmation(self, user_input: str) -> str:
        """Handle information confirmation"""
        user_input = user_input.lower().strip()
        
        if any(word in user_input for word in ['yes', 'correct', 'right', 'confirm', 'y']):
            self.state = FormState.COMPLETED
            return "Perfect! I've recorded your information. We'll call you at your preferred time. Thank you!"
        
        elif any(word in user_input for word in ['no', 'wrong', 'incorrect', 'change', 'n']):
            # Allow user to specify what to change
            if 'name' in user_input:
                self.state = FormState.COLLECTING_NAME
                return "Let's update your name. What's your full name?"
            elif 'email' in user_input:
                self.state = FormState.COLLECTING_EMAIL
                return "Let's update your email. What's your email address?"
            elif 'phone' in user_input:
                self.state = FormState.COLLECTING_PHONE
                return "Let's update your phone number. What's your phone number?"
            elif 'date' in user_input:
                self.state = FormState.COLLECTING_DATE
                return "Let's update your preferred date. When would you like us to call you?"
            else:
                # Restart from the beginning
                self.state = FormState.COLLECTING_NAME
                self.user_info = UserInfo()
                return "Let's start over. What's your full name?"
        
        else:
            return "Please answer 'yes' if the information is correct, or 'no' if you'd like to make changes."
    
    def _generate_confirmation_message(self) -> str:
        """Generate confirmation message with collected information"""
        message = "Let me confirm your information:\n\n"
        message += f"Name: {self.user_info.name}\n"
        message += f"Email: {self.user_info.email}\n"
        message += f"Phone: {self.user_info.phone}\n"
        message += f"Preferred call date: {self.user_info.preferred_date}\n\n"
        message += "Is this information correct? (yes/no)"
        return message
    
    def reset_form(self):
        """Reset the form to initial state"""
        self.state = FormState.INACTIVE
        self.user_info = UserInfo()
        self.retry_count = 0
    
    def is_active(self) -> bool:
        """Check if form is currently active"""
        return self.state != FormState.INACTIVE and self.state != FormState.COMPLETED
    
    def is_completed(self) -> bool:
        """Check if form is completed"""
        return self.state == FormState.COMPLETED
    
    def get_current_state(self) -> str:
        """Get current form state"""
        return self.state.value
    
    def get_collected_info(self) -> Dict[str, Any]:
        """Get currently collected information"""
        return self.user_info.dict(exclude_none=True)