from typing import Optional, List, Dict, Any
from app.services.clinic_data import get_clinic_data


def lookup_patient(name: Optional[str] = None, phone: Optional[str] = None) -> Dict[str, Any]:
    """
    Search for patients by name or phone.
    Returns a dict with 'candidates' (list of matching patients).
    Never guess when multiple patients match.
    """
    clinic = get_clinic_data()
    candidates = []
    
    if phone:
        patient = clinic.get_patient_by_phone(phone)
        if patient:
            candidates.append(patient)
    elif name:
        # First try exact match
        exact_matches = clinic.get_patients_by_name(name)
        if exact_matches:
            candidates = exact_matches
        else:
            # Then try partial match
            candidates = clinic.search_patients_by_partial_name(name)
    
    return {
        "candidates": candidates
    }


def can_caller_access_patient(caller_identifier: Optional[str], patient_id: str, 
                              patient_phone: Optional[str], caller_phone: Optional[str] = None) -> bool:
    """
    Check if a caller is authorized to access a patient's record.
    
    Authorization is granted if:
    1. The caller is the patient themselves (verified by phone or identity)
    2. The caller is a guardian of the patient
    """
    clinic = get_clinic_data()
    patient = clinic.get_patient(patient_id)
    
    if not patient:
        return False
    
    # If caller_identifier is actually a patient_id (e.g., "pt_0001"), check authorization
    if caller_identifier and caller_identifier.startswith("pt_"):
        caller_patient = clinic.get_patient(caller_identifier)
        if not caller_patient:
            return False
        
        # Caller is accessing their own record
        if caller_patient.get("id") == patient_id:
            return True
        
        # Caller is a guardian of the patient
        if patient_id in caller_patient.get("guardian_of", []):
            return True
        
        return False
    
    # If caller_phone provided, check if it matches the patient
    if caller_phone and patient.get("phone") == caller_phone:
        return True
    
    # Check if caller_phone belongs to a guardian
    if caller_phone:
        for p in clinic.patients:
            if p.get("phone") == caller_phone:
                if patient_id in p.get("guardian_of", []):
                    return True
    
    return False


def get_patient_current_appointments(patient_id: str) -> List[Dict[str, Any]]:
    """Get all current/future appointments for a patient."""
    clinic = get_clinic_data()
    return clinic.get_patient_appointments(patient_id)


def resolve_patient_from_candidates(candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    If there's exactly one candidate, return it.
    Otherwise return None (ambiguous).
    """
    if len(candidates) == 1:
        return candidates[0]
    return None
