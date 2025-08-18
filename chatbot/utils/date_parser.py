import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from dateutil.parser import parse
from dateutil.relativedelta import relativedelta


class DateParser:
    @staticmethod
    def parse_relative_date(date_text: str) -> Optional[str]:
        """Parse relative dates like 'next monday', 'tomorrow', etc."""
        date_text = date_text.lower().strip()
        today = datetime.now()
        
        # Handle "today"
        if "today" in date_text:
            return today.strftime("%Y-%m-%d")
        
        # Handle "tomorrow"
        if "tomorrow" in date_text:
            return (today + timedelta(days=1)).strftime("%Y-%m-%d")
        
        # Handle "day after tomorrow"
        if "day after tomorrow" in date_text:
            return (today + timedelta(days=2)).strftime("%Y-%m-%d")
        
        # Handle "next week"
        if "next week" in date_text:
            next_week = today + timedelta(weeks=1)
            # Default to Monday of next week
            days_ahead = 0 - next_week.weekday()  # Monday is 0
            if days_ahead <= 0:
                days_ahead += 7
            target_date = next_week + timedelta(days=days_ahead)
            return target_date.strftime("%Y-%m-%d")
        
        # Handle specific weekdays
        weekdays = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        for day_name, day_num in weekdays.items():
            if day_name in date_text:
                days_ahead = day_num - today.weekday()
                
                if "next" in date_text:
                    # Next occurrence of the weekday
                    if days_ahead <= 0:
                        days_ahead += 7
                elif "this" in date_text:
                    # This week's occurrence
                    if days_ahead < 0:
                        days_ahead += 7
                else:
                    # Default to next occurrence
                    if days_ahead <= 0:
                        days_ahead += 7
                
                target_date = today + timedelta(days=days_ahead)
                return target_date.strftime("%Y-%m-%d")
        
        # Handle "next month"
        if "next month" in date_text:
            next_month = today + relativedelta(months=1)
            return next_month.replace(day=1).strftime("%Y-%m-%d")
        
        return None
    
    @staticmethod
    def parse_absolute_date(date_text: str) -> Optional[str]:
        """Parse absolute dates like '2024-01-15', 'January 15, 2024', etc."""
        try:
            parsed_date = parse(date_text, fuzzy=True)
            return parsed_date.strftime("%Y-%m-%d")
        except (ValueError, TypeError):
            return None
    
    @staticmethod
    def extract_date_from_text(text: str) -> Optional[str]:
        """Extract and parse date from natural language text"""
        # First try relative date parsing
        relative_date = DateParser.parse_relative_date(text)
        if relative_date:
            return relative_date
        
        # Try absolute date parsing
        absolute_date = DateParser.parse_absolute_date(text)
        if absolute_date:
            return absolute_date
        
        # Try to find date patterns in the text
        date_patterns = [
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{2}/\d{2}/\d{4}',  # MM/DD/YYYY
            r'\d{2}-\d{2}-\d{4}',  # MM-DD-YYYY
            r'[A-Za-z]+ \d{1,2}, \d{4}',  # Month DD, YYYY
            r'\d{1,2} [A-Za-z]+ \d{4}',  # DD Month YYYY
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    parsed_date = parse(match.group(), fuzzy=True)
                    return parsed_date.strftime("%Y-%m-%d")
                except (ValueError, TypeError):
                    continue
        
        return None
    
    @staticmethod
    def validate_future_date(date_str: str) -> bool:
        """Check if the date is in the future"""
        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.date() >= datetime.now().date()
        except ValueError:
            return False