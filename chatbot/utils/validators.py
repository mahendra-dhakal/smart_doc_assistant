import re
from typing import Dict, Any
from email_validator import validate_email, EmailNotValidError
import phonenumbers
from phonenumbers import NumberParseException


class ValidationError(Exception):
    """Custom exception for validation errors"""
    pass


class InputValidator:
    @staticmethod
    def validate_name(name: str) -> str:
        """Validate and clean name input"""
        if not name or not name.strip():
            raise ValidationError("Name cannot be empty")
        
        cleaned_name = name.strip()
        if len(cleaned_name) < 2:
            raise ValidationError("Name must be at least 2 characters long")
        
        if not re.match(r"^[a-zA-Z\s'-]+$", cleaned_name):
            raise ValidationError("Name can only contain letters, spaces, hyphens, and apostrophes")
        
        return cleaned_name.title()
    
    @staticmethod
    def validate_email(email: str) -> str:
        """Validate email address"""
        if not email or not email.strip():
            raise ValidationError("Email cannot be empty")
        
        try:
            validated_email = validate_email(email.strip())
            return validated_email.email
        except EmailNotValidError as e:
            raise ValidationError(f"Invalid email format: {str(e)}")
    
    @staticmethod
    def validate_phone(phone: str, default_region: str = "NP") -> str:
        """Validate and format phone number"""
        if not phone or not phone.strip():
            raise ValidationError("Phone number cannot be empty")
        
        try:
            parsed_number = phonenumbers.parse(phone.strip(), default_region)
            
            if not phonenumbers.is_valid_number(parsed_number):
                raise ValidationError("Invalid phone number")
            
            # Return formatted phone number
            return phonenumbers.format_number(parsed_number, phonenumbers.PhoneNumberFormat.INTERNATIONAL)
        
        except NumberParseException as e:
            raise ValidationError(f"Invalid phone number format: {str(e)}")
    
    @staticmethod
    def validate_user_info(user_info: Dict[str, Any]) -> Dict[str, str]:
        """Validate complete user information"""
        validated_info = {}
        
        if "name" in user_info:
            validated_info["name"] = InputValidator.validate_name(user_info["name"])
        
        if "email" in user_info:
            validated_info["email"] = InputValidator.validate_email(user_info["email"])
        
        if "phone" in user_info:
            validated_info["phone"] = InputValidator.validate_phone(user_info["phone"], "NP")
        
        return validated_info