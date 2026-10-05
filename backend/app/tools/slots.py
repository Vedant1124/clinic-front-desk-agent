from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, time
from app.services.clinic_data import get_clinic_data
from app.services.date_utils import get_day_of_week


def search_slots(doctor_id: str, date: str, time_preference: Optional[str] = None) -> Dict[str, Any]:
    """
    Search for available appointment slots for a doctor on a specific date.
    
    Respects:
    - Doctor working days
    - Working hours
    - Slot duration
    - Holidays
    - Doctor leave
    - Existing appointments
    
    Never invents a slot. Returns only genuinely available slots.
    
    Args:
        doctor_id: Doctor's ID (e.g., "dr_rao")
        date: Date in YYYY-MM-DD format
        time_preference: Optional preference like "subah", "dopahar", "shaam"
    
    Returns:
        Dict with 'slots' containing available slot times
    """
    clinic = get_clinic_data()
    
    # Validate the doctor
    doctor = clinic.get_doctor(doctor_id)
    if not doctor:
        return {"slots": []}
    
    # Check if date is a holiday
    if clinic.is_holiday(date):
        return {"slots": []}
    
    # Check if doctor is on leave
    if date in doctor.get("leave_dates", []):
        return {"slots": []}
    
    # Get day of week
    day_of_week = get_day_of_week(date)
    
    # Get working windows for this day
    windows = []
    for window in doctor.get("windows", []):
        if window.get("day") == day_of_week:
            windows.append(window)
    
    if not windows:
        return {"slots": []}
    
    # Get existing appointments for this doctor on this date
    existing_appointments = clinic.get_doctor_appointments(doctor_id, date)
    booked_slots = set()
    for apt in existing_appointments:
        if apt.get("status") in ["booked", "confirmed"]:
            booked_slots.add(apt.get("start"))
    
    # Generate all possible slots
    slot_duration = clinic.clinic_info.get("slot_minutes", 15)
    available_slots = []
    
    for window in windows:
        start_str = window.get("start")  # "09:00"
        end_str = window.get("end")      # "12:00"
        
        try:
            start_time = datetime.strptime(start_str, "%H:%M")
            end_time = datetime.strptime(end_str, "%H:%M")
        except:
            continue
        
        # Generate slots in this window
        current = start_time
        while current < end_time:
            slot_end = current + timedelta(minutes=slot_duration)
            
            # Check if slot fits within window and doesn't overlap with next window
            if slot_end <= end_time:
                slot_time = current.strftime("%H:%M")
                
                # Check if this slot is not already booked
                if slot_time not in booked_slots:
                    available_slots.append(slot_time)
            
            current = slot_end
    
    # Filter by time preference if provided
    if time_preference:
        from app.services.date_utils import parse_time_preference, time_in_range
        time_range = parse_time_preference(time_preference)
        if time_range:
            available_slots = [s for s in available_slots if time_in_range(s, time_range)]
    
    return {
        "slots": available_slots
    }


def validate_slot_availability(doctor_id: str, date: str, start_time: str) -> bool:
    """
    Check if a specific slot is available.
    
    Args:
        doctor_id: Doctor's ID
        date: Date in YYYY-MM-DD format
        start_time: Start time in HH:MM format
    
    Returns:
        True if slot is available, False otherwise
    """
    result = search_slots(doctor_id, date)
    return start_time in result.get("slots", [])
