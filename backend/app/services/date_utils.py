from datetime import datetime, timedelta, time
from typing import Tuple, Optional
import re


def parse_date_string(date_str: str, today: str) -> Optional[str]:
    """
    Parse a date string (exact or relative) into YYYY-MM-DD format.
    today is a string in YYYY-MM-DD format.
    """
    if not date_str:
        return None
    
    date_str = date_str.strip().lower()
    today_obj = datetime.strptime(today, "%Y-%m-%d").date()
    
    # Try exact date formats first
    for fmt in ["%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%d-%m", "%d/%m"]:
        try:
            parsed = datetime.strptime(date_str, fmt).date()
            if fmt in ["%d-%m", "%d/%m"]:
                # Add current year
                parsed = parsed.replace(year=today_obj.year)
            return parsed.strftime("%Y-%m-%d")
        except ValueError:
            pass
    
    # Handle relative dates in Hindi/Hinglish
    if date_str in ["kal", "कल"] or "kl" in date_str or date_str == "tmrw" or date_str == "tomorrow":
        return (today_obj + timedelta(days=1)).strftime("%Y-%m-%d")
    
    if date_str in ["parso", "परसो", "parson"] or "prs" in date_str or date_str == "day after tomorrow":
        return (today_obj + timedelta(days=2)).strftime("%Y-%m-%d")
    
    if date_str in ["aaj", "आज"] or date_str == "today":
        return today
    
    # Handle day names
    day_map = {
        "monday": 0, "mon": 0,
        "tuesday": 1, "tue": 1,
        "wednesday": 2, "wed": 2,
        "thursday": 3, "thu": 3,
        "friday": 4, "fri": 4,
        "saturday": 5, "sat": 5,
        "sunday": 6, "sun": 6,
    }
    
    if date_str in day_map:
        target_day = day_map[date_str]
        current_day = today_obj.weekday()
        days_ahead = target_day - current_day
        if days_ahead <= 0:
            days_ahead += 7
        return (today_obj + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    # Try English date formats
    date_patterns = [
        (r'(\d{1,2})\s+(?:october|oct|10)', lambda m: f"2026-10-{int(m.group(1)):02d}"),
        (r'(\d{1,2})\s+(?:september|sep|09)', lambda m: f"2026-09-{int(m.group(1)):02d}"),
        (r'(\d{1,2})\s+(?:november|nov|11)', lambda m: f"2026-11-{int(m.group(1)):02d}"),  
    ]
    
    for pattern, formatter in date_patterns:
        match = re.search(pattern, date_str)
        if match:
            try:
                result = formatter(match)
                # Validate the date
                datetime.strptime(result, "%Y-%m-%d")
                return result
            except:
                pass
    
    return None


def get_day_of_week(date_str: str) -> str:
    """Get the day of week for a date string (YYYY-MM-DD)."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
    return days[date_obj.weekday()]


def parse_time_preference(time_str: str) -> Optional[Tuple[time, time]]:
    """
    Parse time preference like 'subah', 'dopahar', 'shaam' into a time range.
    Returns (start_time, end_time) or None if not matched.
    """
    if not time_str:
        return None
    
    time_str = time_str.strip().lower()
    
    # Morning preferences: subah, morning, 9am-12pm
    if time_str in ["subah", "सुबह", "morning", "9am", "9-12", "morning slots"]:
        return (time(6, 0), time(12, 0))
    
    # Afternoon preferences: dopahar, afternoon, 12-4pm
    if time_str in ["dopahar", "दोपहर", "afternoon", "12-4", "12pm-4pm", "after lunch"]:
        return (time(12, 0), time(16, 0))
    
    # Evening preferences: shaam, evening, 4-8pm
    if time_str in ["shaam", "शाम", "evening", "4pm", "4-8", "evening slots"]:
        return (time(16, 0), time(20, 0))
    
    # Try to parse exact time like 9:30, 10:00
    try:
        parts = time_str.split(":")
        if len(parts) == 2:
            hour, minute = int(parts[0]), int(parts[1])
            return (time(hour, minute), time(hour, minute + 1))  # Single minute as range
    except:
        pass
    
    return None


def extract_time_range_from_text(text: str) -> Optional[Tuple[time, time]]:
    """Try to extract time range from conversation text."""
    text = text.lower()
    
    # Check for time preferences
    for pref in ["subah", "सुबह", "morning", "dopahar", "दोपहर", "afternoon", "shaam", "शाम", "evening"]:
        if pref in text:
            return parse_time_preference(pref)
    
    # Try to extract explicit times like "9:30" or "10:00"
    time_pattern = r'(\d{1,2}):(\d{2})'
    matches = re.findall(time_pattern, text)
    if matches:
        hour, minute = int(matches[0][0]), int(matches[0][1])
        return (time(hour, minute), time(hour, minute + 1))
    
    return None


def time_in_range(slot_time: str, time_range: Tuple[time, time]) -> bool:
    """Check if a slot time (HH:MM) falls within a time range."""
    try:
        slot = datetime.strptime(slot_time, "%H:%M").time()
        start, end = time_range
        return start <= slot < end
    except:
        return False


def extract_date_from_text(text: str, today: str) -> Optional[str]:
    """
    Extract a date reference from conversation text.
    Handles both exact dates and relative dates.
    """
    text = text.lower()
    
    # Try common date references
    date_patterns = [
        (r'(\d{1,2})\s+(?:october|oct|10)(?:ber)?', lambda m: f"2026-10-{int(m.group(1)):02d}"),
        (r'(\d{1,2})\s+oct\b', lambda m: f"2026-10-{int(m.group(1)):02d}"),
    ]
    
    for pattern, formatter in date_patterns:
        match = re.search(pattern, text)
        if match:
            try:
                result = formatter(match)
                datetime.strptime(result, "%Y-%m-%d")
                return result
            except:
                pass
    
    # Try relative dates
    for keyword, offset in [("kal", 1), ("कल", 1), ("parso", 2), ("परसो", 2), ("aaj", 0), ("आज", 0)]:
        if keyword in text:
            today_obj = datetime.strptime(today, "%Y-%m-%d").date()
            return (today_obj + timedelta(days=offset)).strftime("%Y-%m-%d")
    
    # Try day names
    day_map = {
        "monday": 0, "mon": 0, "tuesday": 1, "tue": 1,
        "wednesday": 2, "wed": 2, "thursday": 3, "thu": 3,
        "friday": 4, "fri": 4, "saturday": 5, "sat": 5, "sunday": 6, "sun": 6,
    }
    
    for day_name, target_day in day_map.items():
        if day_name in text:
            today_obj = datetime.strptime(today, "%Y-%m-%d").date()
            current_day = today_obj.weekday()
            days_ahead = target_day - current_day
            if days_ahead <= 0:
                days_ahead += 7
            return (today_obj + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
    
    return None


def extract_doctor_name_from_text(text: str) -> Optional[str]:
    """Extract doctor name from conversation text."""
    text = text.lower()
    
    # Try to find "dr." mentions
    dr_pattern = r'dr\.?\s+(\w+)'
    match = re.search(dr_pattern, text)
    if match:
        return match.group(1).lower()
    
    # Common doctor name keywords
    if "rao" in text:
        return "rao"
    if "sethi" in text:
        return "sethi"
    
    return None


def is_medical_advice_request(text: str) -> bool:
    """Check if the text is asking for medical advice."""
    text = text.lower()
    
    advice_keywords = [
        "medicine", "tablet", "دوا", "medicine deya", "dawa", "kya dawai",
        "kya le lu", "kya dawai lu", "किस दवा", "दवा", "दवाई",
        "disease", "बीमारी", "beemari", "treatment", "علاج",
        "symptom", "लक्षण", "lakshan", "problem", "health issue",
        "fever", "cough", "cold", "खांसी", "बुखार", "sardi",
        "bukhar", "bukhaar", "crocin", "goli", "goli le", "le lun", "kitni der",
        "pain", "दर्द", "dard", "injection", "vaccine",
        "my symptoms", "i am feeling", "suffering from", "पीड़ित",
        "prescription", "reorder medicine", "renew prescription"
    ]
    
    for keyword in advice_keywords:
        if keyword in text:
            return True
    
    return False


def is_clinical_urgent_situation(text: str) -> bool:
    """Check if the text describes a clinical emergency."""
    text = text.lower()
    
    urgent_keywords = [
        "emergency", "urgent", "ेमरजेंसी", "डॉक्टर को तुरंत",
        "जरूरी", "जरुरी", "severe", "गंभीर", "critical",
        "immediately", "right now", "अभी", "hospital", "हॉस्पिटल",
        "accident", "fall", "गिर गया", "injury", "चोट",
        "bleeding", "खून", "unconscious", "बेहोश", "faint",
        "difficulty breathing", "shortness of breath", "सांस की कमी", "breathless",
        "chest pain", "seene mein dard", "सीने में दर्द", "heart problem", "दिल", "allergic reaction",
        "shock", "seizure", "stroke", "sudden", "अचानक"
    ]
    
    for keyword in urgent_keywords:
        if keyword in text:
            return True
    
    return False
