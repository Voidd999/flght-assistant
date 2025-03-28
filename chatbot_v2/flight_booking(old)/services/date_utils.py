from datetime import datetime, timedelta
import re
from typing import Optional, Tuple

def get_current_date() -> datetime:
    """Get the current date"""
    return datetime.now()

def format_date_for_system(date_obj: datetime) -> str:
    """Format a datetime object into MM/DD/YYYY format for internal use"""
    return date_obj.strftime("%m/%d/%Y")

def parse_relative_date(date_text: str) -> Optional[datetime]:
    """
    Parse relative date expressions like "tomorrow", "next week", etc.
    Returns a datetime object or None if parsing fails
    """
    today = get_current_date()
    date_text = date_text.lower().strip()
    
    if date_text in ["today", "now"]:
        return today
    elif date_text in ["tomorrow", "tmrw", "tmr"]:
        return today + timedelta(days=1)
    elif date_text in ["day after tomorrow"]:
        return today + timedelta(days=2)
    elif "next week" in date_text:
        return today + timedelta(days=7)
    elif "next month" in date_text:
        if today.month == 12:
            return datetime(today.year + 1, 1, today.day)
        else:
            next_month = today.month + 1
            day = min(today.day, [31, 29 if today.year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][next_month-1])
            return datetime(today.year, next_month, day)
    
    in_days_match = re.search(r"in\s+(\d+)\s+days?", date_text)
    if in_days_match:
        days = int(in_days_match.group(1))
        return today + timedelta(days=days)
    
    in_weeks_match = re.search(r"in\s+(\d+)\s+weeks?", date_text)
    if in_weeks_match:
        weeks = int(in_weeks_match.group(1))
        return today + timedelta(days=weeks*7)
    
    return None

def is_valid_booking_date(date_str: str) -> Tuple[bool, Optional[str]]:
    """
    Check if a date string is valid for booking.
    Returns a tuple (is_valid, formatted_date_string).
    If date is invalid, formatted_date_string will be None.
    """
    today = get_current_date()
    
    try:
        date_obj = datetime.strptime(date_str, "%m/%d/%Y")
    except ValueError:
        date_obj = parse_relative_date(date_str)
        
        if not date_obj:
            return False, None
    
    if date_obj.date() < today.date():
        return False, None
    
    formatted_date = format_date_for_system(date_obj)
    return True, formatted_date