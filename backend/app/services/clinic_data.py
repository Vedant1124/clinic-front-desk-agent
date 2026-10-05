import json
from pathlib import Path
from typing import Optional, Dict, List, Any


class ClinicData:
    """Load and expose clinic.json data."""
    
    def __init__(self, clinic_json_path: Optional[str] = None):
        if clinic_json_path is None:
            clinic_json_path = Path(__file__).parent.parent.parent / "clinic.json"
        
        with open(clinic_json_path, 'r') as f:
            self.data = json.load(f)
    
    @property
    def clinic_info(self) -> Dict[str, Any]:
        """Get clinic metadata."""
        return self.data.get("clinic", {})
    
    @property
    def doctors(self) -> List[Dict[str, Any]]:
        """Get all doctors."""
        return self.data.get("doctors", [])
    
    @property
    def patients(self) -> List[Dict[str, Any]]:
        """Get all patients."""
        return self.data.get("patients", [])
    
    @property
    def appointments(self) -> List[Dict[str, Any]]:
        """Get all appointments."""
        return self.data.get("appointments", [])
    
    @property
    def holidays(self) -> List[str]:
        """Get holiday dates as list of YYYY-MM-DD strings."""
        return self.data.get("holidays", [])
    
    def get_doctor(self, doctor_id: str) -> Optional[Dict[str, Any]]:
        """Get a doctor by ID."""
        for doc in self.doctors:
            if doc.get("id") == doctor_id:
                return doc
        return None
    
    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        """Get a patient by ID."""
        for patient in self.patients:
            if patient.get("id") == patient_id:
                return patient
        return None
    
    def get_patient_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Get a patient by phone number."""
        for patient in self.patients:
            if patient.get("phone") == phone:
                return patient
        return None
    
    def get_patients_by_name(self, name: str) -> List[Dict[str, Any]]:
        """Get all patients matching a name (case-insensitive)."""
        name_lower = name.lower()
        matches = []
        for patient in self.patients:
            patient_name = patient.get("name", "").lower()
            if patient_name == name_lower:
                matches.append(patient)
        return matches
    
    def search_patients_by_partial_name(self, partial_name: str) -> List[Dict[str, Any]]:
        """Get patients matching a partial name (case-insensitive, word-based).
        
        Searches by checking if any word from the search term appears in the patient name.
        This supports colloquial/partial names like "Sharma ji" matching "Amit Sharma".
        """
        partial_lower = partial_name.lower()
        search_words = partial_lower.split()
        
        matches = []
        for patient in self.patients:
            patient_name = patient.get("name", "").lower()
            
            # Check if any word from search appears in patient name
            for word in search_words:
                if word in patient_name:
                    matches.append(patient)
                    break  # Don't add the same patient multiple times
        
        return matches
    
    def get_appointment(self, appointment_id: str) -> Optional[Dict[str, Any]]:
        """Get an appointment by ID."""
        for apt in self.appointments:
            if apt.get("id") == appointment_id:
                return apt
        return None
    
    def get_patient_appointments(self, patient_id: str) -> List[Dict[str, Any]]:
        """Get all appointments for a patient."""
        return [apt for apt in self.appointments if apt.get("patient_id") == patient_id]
    
    def get_doctor_appointments(self, doctor_id: str, date: str) -> List[Dict[str, Any]]:
        """Get all appointments for a doctor on a specific date."""
        return [apt for apt in self.appointments 
                if apt.get("doctor_id") == doctor_id and apt.get("date") == date]
    
    def is_holiday(self, date: str) -> bool:
        """Check if a date is a holiday."""
        return date in self.holidays
    
    def get_next_appointment_id(self) -> str:
        """Generate the next appointment ID."""
        ids = [apt.get("id") for apt in self.appointments]
        max_num = 0
        for id_str in ids:
            if id_str and id_str.startswith("ap_"):
                try:
                    num = int(id_str[3:])
                    max_num = max(max_num, num)
                except ValueError:
                    pass
        return f"ap_{max_num + 1:04d}"
    
    def add_appointment(self, appointment: Dict[str, Any]) -> None:
        """Add a new appointment to the data."""
        self.data["appointments"].append(appointment)
    
    def update_appointment(self, appointment_id: str, updates: Dict[str, Any]) -> bool:
        """Update an appointment with new values."""
        for apt in self.appointments:
            if apt.get("id") == appointment_id:
                apt.update(updates)
                return True
        return False
    
    def remove_appointment(self, appointment_id: str) -> bool:
        """Remove an appointment."""
        for i, apt in enumerate(self.appointments):
            if apt.get("id") == appointment_id:
                self.appointments.pop(i)
                return True
        return False


# Global instance
_clinic_data = None


def get_clinic_data() -> ClinicData:
    """Get the clinic data singleton."""
    global _clinic_data
    if _clinic_data is None:
        _clinic_data = ClinicData()
    return _clinic_data
