from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from app.services.clinic_data import get_clinic_data
from app.tools.slots import validate_slot_availability


def book_appointment(patient_id: str, doctor_id: str, date: str, start: str) -> Dict[str, Any]:
    """
    Book a new appointment for a patient with a doctor.
    
    Validates:
    - Patient exists
    - Doctor exists
    - Requested slot is available
    - No double booking
    
    Args:
        patient_id: Patient's ID
        doctor_id: Doctor's ID
        date: Date in YYYY-MM-DD format
        start: Start time in HH:MM format
    
    Returns:
        Dict with 'success' (bool) and 'appointment_id' or 'error'
    """
    clinic = get_clinic_data()
    
    # Validate patient
    patient = clinic.get_patient(patient_id)
    if not patient:
        return {"success": False, "error": "Patient not found"}
    
    # Validate doctor
    doctor = clinic.get_doctor(doctor_id)
    if not doctor:
        return {"success": False, "error": "Doctor not found"}
    
    # Check if slot is available
    if not validate_slot_availability(doctor_id, date, start):
        return {"success": False, "error": "Slot not available"}
    
    # Check for double booking - patient shouldn't have appointment at same time with same doctor
    existing_apts = clinic.get_patient_appointments(patient_id)
    for apt in existing_apts:
        if apt.get("date") == date and apt.get("start") == start and apt.get("doctor_id") == doctor_id:
            return {"success": False, "error": "Patient already has an appointment at this time with this doctor"}
    
    # Calculate end time (assuming 15 minute slots)
    slot_duration = clinic.clinic_info.get("slot_minutes", 15)
    start_dt = datetime.strptime(start, "%H:%M")
    end_dt = start_dt + timedelta(minutes=slot_duration)
    end_time = end_dt.strftime("%H:%M")
    
    # Create appointment
    appointment_id = clinic.get_next_appointment_id()
    appointment = {
        "id": appointment_id,
        "patient_id": patient_id,
        "doctor_id": doctor_id,
        "date": date,
        "start": start,
        "end": end_time,
        "status": "booked"
    }
    
    clinic.add_appointment(appointment)
    
    return {
        "success": True,
        "appointment_id": appointment_id
    }


def reschedule_appointment(appointment_id: str, new_date: str, new_start: str) -> Dict[str, Any]:
    """
    Reschedule an existing appointment to a new date and time.
    
    Validates:
    - Appointment exists
    - New slot is available
    - No double booking at new slot
    
    Args:
        appointment_id: The appointment to reschedule
        new_date: New date in YYYY-MM-DD format
        new_start: New start time in HH:MM format
    
    Returns:
        Dict with 'success' (bool) and 'appointment_id' or 'error'
    """
    clinic = get_clinic_data()
    
    # Get the appointment
    appointment = clinic.get_appointment(appointment_id)
    if not appointment:
        return {"success": False, "error": "Appointment not found"}
    
    doctor_id = appointment.get("doctor_id")
    patient_id = appointment.get("patient_id")
    
    # Check if new slot is available
    if not validate_slot_availability(doctor_id, new_date, new_start):
        return {"success": False, "error": "New slot not available"}
    
    # Check for double booking at new slot
    existing_apts = clinic.get_patient_appointments(patient_id)
    for apt in existing_apts:
        if apt.get("id") != appointment_id:  # Exclude current appointment
            if apt.get("date") == new_date and apt.get("start") == new_start and apt.get("doctor_id") == doctor_id:
                return {"success": False, "error": "Patient already has an appointment at this time with this doctor"}
    
    # Calculate end time
    slot_duration = clinic.clinic_info.get("slot_minutes", 15)
    start_dt = datetime.strptime(new_start, "%H:%M")
    end_dt = start_dt + timedelta(minutes=slot_duration)
    new_end = end_dt.strftime("%H:%M")
    
    # Update appointment
    updates = {
        "date": new_date,
        "start": new_start,
        "end": new_end
    }
    
    clinic.update_appointment(appointment_id, updates)
    
    return {
        "success": True,
        "appointment_id": appointment_id
    }


def cancel_appointment(appointment_id: str) -> Dict[str, Any]:
    """
    Cancel an existing appointment.
    
    Validates:
    - Appointment exists
    
    Args:
        appointment_id: The appointment to cancel
    
    Returns:
        Dict with 'success' (bool) and 'appointment_id' or 'error'
    """
    clinic = get_clinic_data()
    
    # Get the appointment
    appointment = clinic.get_appointment(appointment_id)
    if not appointment:
        return {"success": False, "error": "Appointment not found"}
    
    # Remove the appointment
    if clinic.remove_appointment(appointment_id):
        return {
            "success": True,
            "appointment_id": appointment_id
        }
    else:
        return {"success": False, "error": "Failed to cancel appointment"}


def get_appointment_details(appointment_id: str) -> Dict[str, Any]:
    """Get details of an appointment."""
    clinic = get_clinic_data()
    apt = clinic.get_appointment(appointment_id)
    if apt:
        return {"appointment": apt}
    return {"appointment": None}
