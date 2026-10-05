from typing import Dict, Any, Optional


def escalate_to_human(reason: str) -> Dict[str, Any]:
    """
    Create an escalation result with the given reason.
    
    Supported reasons:
    - clinical_urgent: Caller described a clinical emergency
    - medical_advice: Caller is asking for medical advice
    - not_authorised: Caller is trying to access another patient's record
    - ambiguous_patient: Caller identity is ambiguous
    - out_of_scope: Request is beyond front desk agent capability
    
    Args:
        reason: One of the supported escalation reasons
    
    Returns:
        Dict with escalation details
    """
    valid_reasons = [
        "clinical_urgent",
        "medical_advice",
        "not_authorised",
        "ambiguous_patient",
        "out_of_scope"
    ]
    
    if reason not in valid_reasons:
        return {
            "success": False,
            "error": f"Invalid escalation reason: {reason}"
        }
    
    return {
        "success": True,
        "terminal_state": "escalated",
        "escalation_reason": reason
    }
