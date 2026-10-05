import json
import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from dotenv import load_dotenv
from groq import Groq

from app.models import AgentResponse, Metrics, ToolCall
from app.services.clinic_data import get_clinic_data
from app.services.date_utils import (
    is_clinical_urgent_situation,
    is_medical_advice_request,
    parse_date_string,
    parse_time_preference,
    time_in_range,
)
from app.tools import appointments as appointments_tool
from app.tools import escalation as escalation_tool
from app.tools import patient as patient_tool
from app.tools import slots as slots_tool

load_dotenv()

_groq_key = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=_groq_key) if _groq_key else None


class ConversationContext:
    def __init__(self):
        self.intent: Optional[str] = None
        self.patient_name: Optional[str] = None
        self.patient_phone: Optional[str] = None

        self.caller_name: Optional[str] = None
        self.caller_phone: Optional[str] = None
        self.caller_relationship: Optional[str] = None

        self.doctor_name: Optional[str] = None
        self.doctor_id: Optional[str] = None

        self.requested_date: Optional[str] = None
        self.requested_time: Optional[str] = None
        self.time_preference: Optional[str] = None

        self.current_date: Optional[str] = None
        self.current_time: Optional[str] = None
        self.current_doctor_name: Optional[str] = None
        self.current_doctor_id: Optional[str] = None

        self.appointment_id: Optional[str] = None
        self.tokens_used: int = 0


class Agent:
    """LLM handles conversation understanding; tools handle clinic facts and mutations."""

    def __init__(self):
        self.clinic = get_clinic_data()

    def run(self, conversation_id: str, today: str, turns: List[Any]) -> AgentResponse:
        self._reset_clinic_state()
        self.clinic = get_clinic_data()

        turn_texts = self._normalise_turns(turns)

        for text in turn_texts:
            if is_clinical_urgent_situation(text):
                return self._escalate(
                    conversation_id,
                    "clinical_urgent",
                    len(turn_texts),
                    0,
                    "Kripaya turant medical sahayata lein. (Please seek immediate medical help.)",
                )

            if is_medical_advice_request(text):
                return self._escalate(
                    conversation_id,
                    "medical_advice",
                    len(turn_texts),
                    0,
                    "Main medical salah nahi de sakta. Main aapko human support se connect karta hoon.",
                )

        if self._is_unsupported_request(turn_texts):
            return self._build_response(
                conversation_id,
                "refused",
                "Yeh operation front-desk agent ke available capabilities mein nahi hai.",
                len(turn_texts),
                tokens=0,
            )

        context, tokens_used = self._extract_context_with_llm(turn_texts, today)

        # If the LLM classified the conversation as out_of_scope but the raw
        # turns clearly contain booking signals (appointment/doctor/dr or a
        # 10-digit phone), prefer treating this as a booking intent. This
        # prevents misclassification when callers simply provide patient
        # info across turns and the LLM incorrectly returns out_of_scope.
        combined_text = " ".join(turn_texts).lower()

        if self._is_unsupported_request(turn_texts):
            context.intent = "out_of_scope"
        elif "cancel" in combined_text or "रद्द" in combined_text:
            context.intent = "cancel"
        elif "reschedule" in combined_text or "change appointment" in combined_text or "shift" in combined_text:
            context.intent = "reschedule"
        elif (
            any(word in combined_text for word in ["appointment", "doctor", "dr.", "book", "dikhana", "dikhana hai"])
            and (context.patient_name or context.patient_phone)
        ):
            context.intent = "book"
        elif re.search(r"\b\d{10}\b", combined_text) and context.patient_name:
            context.intent = "book"
        else:
            context.intent = "abandon"

        if not context.intent or context.intent == "abandon":
            return self._build_response(
                conversation_id,
                "abandoned",
                "Kripaya zyada jankari dein. (Please provide more information.)",
                len(turn_texts),
                tokens=tokens_used,
            )

        if context.intent == "out_of_scope":
            return self._build_response(
                conversation_id,
                "refused",
                "Yeh operation front-desk agent ke available capabilities mein nahi hai.",
                len(turn_texts),
                tokens=tokens_used,
            )

        if context.intent == "book":
            return self._handle_booking(conversation_id, context, turn_texts, tokens_used)
        if context.intent == "reschedule":
            return self._handle_rescheduling(conversation_id, context, turn_texts, tokens_used)
        if context.intent == "cancel":
            return self._handle_cancellation(conversation_id, context, turn_texts, tokens_used)

        return self._build_response(
            conversation_id,
            "abandoned",
            "Kripaya zyada jankari dein.",
            len(turn_texts),
            tokens=tokens_used,
        )

    def _extract_context_with_llm(self, turns: List[str], today: str) -> Tuple[ConversationContext, int]:
        context = ConversationContext()

        if not groq_client:
            return self._fallback_context(turns, today), 0

        conversation_text = "\n".join(f"Turn {index + 1}: {text}" for index, text in enumerate(turns))

        prompt = f"""You extract structured information for a clinic front-desk agent.

Today's date is {today}.
Read ALL conversation turns below and combine information across turns into one final JSON object.
- Extract `patient_name` and `patient_phone` from ANY turn where they appear.
- Preserve patient information mentioned in earlier turns unless a later turn explicitly supplies a different patient name or phone.
- Latest corrections should override earlier values only for date, time, or doctor.

CONVERSATION:
{conversation_text}

Return ONLY valid JSON, no markdown.
{{
    "intent": "book" | "reschedule" | "cancel" | "abandon" | "out_of_scope",
    "patient_name": "string or null",
    "patient_phone": "10-digit phone or null",
    "caller_name": "string or null",
    "caller_phone": "10-digit phone or null",
    "caller_relationship": "string or null",
    "doctor_name": "string or null",
    "requested_date": "YYYY-MM-DD or null",
    "requested_time": "HH:MM or null",
    "time_preference": "subah" | "dopahar" | "shaam" | null,
    "current_date": "YYYY-MM-DD or null",
    "current_time": "HH:MM or null",
    "current_doctor_name": "string or null",
    "appointment_id": "string or null"
}}
Rules:
- patient_name = patient whose record is being acted on.
- caller_name/caller_phone = person speaking.
- If a later turn corrects date/time/doctor, use the latest value for those fields.
- Preserve patient_name and patient_phone across turns unless explicitly changed.
- Relative dates: kal/tomorrow = +1 day, parso/day after tomorrow = +2 days.
- Exact time beats broad preference.
- Never guess a patient, doctor, date, time, phone, or appointment id; use null when unclear.
- Unsupported admin/bulk requests should become "out_of_scope".
"""

        try:
            print("GROQ CALL STARTED")
            response = groq_client.chat.completions.create(
                model="openai/gpt-oss-20b",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0,
                max_tokens=1000,
            )
            print("GROQ CALL SUCCESS")
            raw = (response.choices[0].message.content or "").strip()
            print("GROQ RAW RESPONSE:", raw)
            data = json.loads(self._clean_json(raw))
            tokens = int(getattr(response.usage, "total_tokens", 0) or 0)

            context.intent = data.get("intent")
            context.patient_name = self._normalise_name(data.get("patient_name"))
            context.patient_phone = self._normalise_phone(data.get("patient_phone"))
            context.caller_name = self._normalise_name(data.get("caller_name"))
            context.caller_phone = self._normalise_phone(data.get("caller_phone"))
            context.caller_relationship = data.get("caller_relationship")
            context.doctor_name = self._normalise_name(data.get("doctor_name"))
            context.doctor_id = self._doctor_id(context.doctor_name)
            context.requested_date = self._normalise_date(data.get("requested_date"), today)
            context.requested_time = self._normalise_time(data.get("requested_time"))
            context.time_preference = (data.get("time_preference") or "").strip().lower() or None
            context.current_date = self._normalise_date(data.get("current_date"), today)
            context.current_time = self._normalise_time(data.get("current_time"))
            context.current_doctor_name = self._normalise_name(data.get("current_doctor_name"))
            context.current_doctor_id = self._doctor_id(context.current_doctor_name)
            context.appointment_id = data.get("appointment_id")
            context.tokens_used = tokens
            return context, tokens
        except Exception as e:
            print("GROQ ERROR:", repr(e))
            return self._fallback_context(turns, today), 0
            

    def _handle_booking(
        self,
        conversation_id: str,
        context: ConversationContext,
        turns: List[str],
        tokens: int,
    ) -> AgentResponse:
        tool_calls: List[ToolCall] = []

        patient, call_list, status = self._resolve_patient(context)
        tool_calls.extend(call_list)

        if status == "ambiguous":
            return self._escalate(
                conversation_id,
                "ambiguous_patient",
                len(turns),
                tokens,
                "Patient ki identity clear nahi hai. Main human support se help karwata hoon.",
                tool_calls,
            )

        if status == "not_found":
            return self._build_response(
                conversation_id,
                "abandoned",
                "Kripaya patient ka naam ya phone number confirm karein.",
                len(turns),
                tokens=tokens,
                tool_calls=tool_calls,
            )

        if not patient:
            return self._build_response(
                conversation_id,
                "abandoned",
                "Kripaya patient ki identification dein.",
                len(turns),
                tokens=tokens,
                tool_calls=tool_calls,
            )

        patient_id = patient["id"]

        if not self._authorised(context, patient_id):
            return self._escalate(
                conversation_id,
                "not_authorised",
                len(turns),
                tokens,
                "Caller authorization verify nahi ho saki.",
                tool_calls,
            )

        if not context.doctor_id:
            return self._build_response(
                conversation_id,
                "abandoned",
                "Kripaya doctor ka naam bataiye.",
                len(turns),
                patient_id=patient_id,
                tokens=tokens,
                tool_calls=tool_calls,
            )

        if not context.requested_date:
            return self._build_response(
                conversation_id,
                "abandoned",
                "Kripaya appointment ki date bataiye.",
                len(turns),
                patient_id=patient_id,
                tokens=tokens,
                tool_calls=tool_calls,
            )

        search_args = {"doctor_id": context.doctor_id, "date": context.requested_date}
        if context.time_preference and context.requested_time is None:
            search_args["time_preference"] = context.time_preference
            search_result = slots_tool.search_slots(context.doctor_id, context.requested_date, context.time_preference)
        else:
            search_result = slots_tool.search_slots(context.doctor_id, context.requested_date)
        tool_calls.append(ToolCall(name="search_slots", arguments=search_args))

        available_slots = search_result.get("slots", [])
        if not available_slots:
            return self._build_response(
                conversation_id,
                "abandoned",
                "Us din us doctor ke paas koi available slot nahi hai.",
                len(turns),
                patient_id=patient_id,
                tokens=tokens,
                tool_calls=tool_calls,
            )

        # If user is only asking for availability, don't automatically book
        if self._is_availability_only_request(turns):
            slots_text = ", ".join(available_slots)
            return self._build_response(
                conversation_id,
                "availability_shown",
                f"{context.requested_date} ko {context.doctor_name} ke saath ye slots available hain: {slots_text}. Kaunsa slot select karna chahte hain?",
                len(turns),
                patient_id=patient_id,
                tokens=tokens,
                tool_calls=tool_calls,
            )

        selected_slot: Optional[str] = None

        if context.requested_time is not None:
            if context.requested_time in available_slots:
                selected_slot = context.requested_time
            else:
                return self._build_response(
                    conversation_id,
                    "abandoned",
                    f"{context.requested_time} par slot available nahi hai. Main doosra time without confirmation nahi book karunga.",
                    len(turns),
                    patient_id=patient_id,
                    tokens=tokens,
                    tool_calls=tool_calls,
                )
        elif context.time_preference:
            time_range = parse_time_preference(context.time_preference)
            if time_range:
                filtered = [slot for slot in available_slots if time_in_range(slot, time_range)]
                if not filtered:
                    return self._build_response(
                        conversation_id,
                        "abandoned",
                        "Us preference ke according koi slot available nahi hai.",
                        len(turns),
                        patient_id=patient_id,
                        tokens=tokens,
                        tool_calls=tool_calls,
                    )
                selected_slot = filtered[0]
            else:
                selected_slot = available_slots[0]
        else:
            selected_slot = available_slots[0]

        booking_result = appointments_tool.book_appointment(
            patient_id=patient_id,
            doctor_id=context.doctor_id,
            date=context.requested_date,
            start=selected_slot,
        )
        tool_calls.append(
            ToolCall(
                name="book_appointment",
                arguments={
                    "patient_id": patient_id,
                    "doctor_id": context.doctor_id,
                    "date": context.requested_date,
                    "start": selected_slot,
                },
            )
        )

        if not booking_result.get("success"):
            return self._build_response(
                conversation_id,
                "abandoned",
                booking_result.get("error", "Appointment book nahi ho paya."),
                len(turns),
                patient_id=patient_id,
                tokens=tokens,
                tool_calls=tool_calls,
            )

        doctor_name = self.clinic.get_doctor(context.doctor_id).get("name", "Doctor") if self.clinic.get_doctor(context.doctor_id) else "Doctor"
        appointment_id = booking_result.get("appointment_id")
        return self._build_response(
            conversation_id,
            "booked",
            f"Bilkul, {context.requested_date} ko {selected_slot} par {doctor_name} ke saath appointment book ho gaya.",
            len(turns),
            patient_id=patient_id,
            appointment_id=appointment_id,
            tokens=tokens,
            tool_calls=tool_calls,
        )

    def _handle_rescheduling(
        self,
        conversation_id: str,
        context: ConversationContext,
        turns: List[str],
        tokens: int,
    ) -> AgentResponse:
        tool_calls: List[ToolCall] = []

        patient, call_list, status = self._resolve_patient(context)
        tool_calls.extend(call_list)

        if status == "ambiguous":
            return self._escalate(
                conversation_id,
                "ambiguous_patient",
                len(turns),
                tokens,
                "Patient ki identity clear nahi hai.",
                tool_calls,
            )

        if status != "ok" or not patient:
            return self._build_response(
                conversation_id,
                "abandoned",
                "Kripaya patient ki identification confirm karein.",
                len(turns),
                tokens=tokens,
                tool_calls=tool_calls,
            )

        patient_id = patient["id"]
        if not self._authorised(context, patient_id):
            return self._escalate(
                conversation_id,
                "not_authorised",
                len(turns),
                tokens,
                "Caller authorization verify nahi ho saki.",
                tool_calls,
            )

        appointment = self._find_appointment(
            patient_id=patient_id,
            appointment_id=context.appointment_id,
            date=context.current_date,
            time=context.current_time,
            doctor_id=context.current_doctor_id or context.doctor_id,
        )

        if not appointment:
            return self._build_response(
                conversation_id,
                "abandoned",
                "Matching existing appointment nahi mila.",
                len(turns),
                patient_id=patient_id,
                tokens=tokens,
                tool_calls=tool_calls,
            )

        target_date = context.requested_date or context.current_date
        target_time = context.requested_time
        if not target_date or not target_time:
            return self._build_response(
                conversation_id,
                "abandoned",
                "Nayi date aur exact time bataiye.",
                len(turns),
                patient_id=patient_id,
                appointment_id=appointment.get("id"),
                tokens=tokens,
                tool_calls=tool_calls,
            )

        doctor_id = appointment.get("doctor_id")
        search_result = slots_tool.search_slots(doctor_id, target_date)
        tool_calls.append(ToolCall(name="search_slots", arguments={"doctor_id": doctor_id, "date": target_date}))
        available = search_result.get("slots", [])
        if target_time not in available:
            return self._build_response(
                conversation_id,
                "abandoned",
                f"{target_time} par slot available nahi hai. Main doosra time bina confirmation ke choose nahi karunga.",
                len(turns),
                patient_id=patient_id,
                appointment_id=appointment.get("id"),
                tokens=tokens,
                tool_calls=tool_calls,
            )

        res_schedule_result = appointments_tool.reschedule_appointment(
            appointment_id=appointment["id"],
            new_date=target_date,
            new_start=target_time,
        )
        tool_calls.append(
            ToolCall(
                name="reschedule_appointment",
                arguments={
                    "appointment_id": appointment["id"],
                    "new_date": target_date,
                    "new_start": target_time,
                },
            )
        )

        if not res_schedule_result.get("success"):
            return self._build_response(
                conversation_id,
                "abandoned",
                res_schedule_result.get("error", "Appointment reschedule nahi ho paya."),
                len(turns),
                patient_id=patient_id,
                appointment_id=appointment.get("id"),
                tokens=tokens,
                tool_calls=tool_calls,
            )

        return self._build_response(
            conversation_id,
            "rescheduled",
            f"Appointment {target_date} ko {target_time} par reschedule ho gaya.",
            len(turns),
            patient_id=patient_id,
            appointment_id=appointment.get("id"),
            tokens=tokens,
            tool_calls=tool_calls,
        )

    def _handle_cancellation(
        self,
        conversation_id: str,
        context: ConversationContext,
        turns: List[str],
        tokens: int,
    ) -> AgentResponse:
        tool_calls: List[ToolCall] = []

        patient, call_list, status = self._resolve_patient(context)
        tool_calls.extend(call_list)

        if status == "ambiguous":
            return self._escalate(
                conversation_id,
                "ambiguous_patient",
                len(turns),
                tokens,
                "Patient ki identity clear nahi hai.",
                tool_calls,
            )

        if status != "ok" or not patient:
            return self._build_response(
                conversation_id,
                "abandoned",
                "Kripaya patient ki identification confirm karein.",
                len(turns),
                tokens=tokens,
                tool_calls=tool_calls,
            )

        patient_id = patient["id"]
        if not self._authorised(context, patient_id):
            return self._escalate(
                conversation_id,
                "not_authorised",
                len(turns),
                tokens,
                "Caller authorization verify nahi ho saki.",
                tool_calls,
            )

        appointment = self._find_appointment(
            patient_id=patient_id,
            appointment_id=context.appointment_id,
            date=context.current_date or context.requested_date,
            time=context.current_time or context.requested_time,
            doctor_id=context.current_doctor_id or context.doctor_id,
        )

        if not appointment:
            return self._build_response(
                conversation_id,
                "abandoned",
                "Matching existing appointment nahi mila.",
                len(turns),
                patient_id=patient_id,
                tokens=tokens,
                tool_calls=tool_calls,
            )

        cancel_result = appointments_tool.cancel_appointment(appointment["id"])
        tool_calls.append(ToolCall(name="cancel_appointment", arguments={"appointment_id": appointment["id"]}))

        if not cancel_result.get("success"):
            return self._build_response(
                conversation_id,
                "abandoned",
                cancel_result.get("error", "Appointment cancel nahi ho paya."),
                len(turns),
                patient_id=patient_id,
                appointment_id=appointment.get("id"),
                tokens=tokens,
                tool_calls=tool_calls,
            )

        return self._build_response(
            conversation_id,
            "cancelled",
            "Aapka appointment cancel ho gaya.",
            len(turns),
            patient_id=patient_id,
            appointment_id=appointment.get("id"),
            tokens=tokens,
            tool_calls=tool_calls,
        )

    def _resolve_patient(self, context: ConversationContext) -> Tuple[Optional[Dict[str, Any]], List[ToolCall], str]:
        tool_calls: List[ToolCall] = []

        candidates: List[Dict[str, Any]] = []

        if context.patient_phone:
            result = patient_tool.lookup_patient(phone=context.patient_phone)
            tool_calls.append(ToolCall(name="lookup_patient", arguments={"phone": context.patient_phone}))
            candidates = result.get("candidates", [])

        if context.patient_name and not candidates:
            result = patient_tool.lookup_patient(name=context.patient_name)
            tool_calls.append(ToolCall(name="lookup_patient", arguments={"name": context.patient_name}))
            candidates = result.get("candidates", [])

        if context.patient_name and context.patient_phone:
            candidates = [p for p in candidates if p.get("phone") == context.patient_phone]

        if len(candidates) == 1:
            return candidates[0], tool_calls, "ok"
        if len(candidates) > 1:
            return None, tool_calls, "ambiguous"
        return None, tool_calls, "not_found"

    def _authorised(self, context: ConversationContext, patient_id: str) -> bool:
        patient = self.clinic.get_patient(patient_id)
        if not patient:
            return False

        # If patient is calling for themselves (no separate caller info)
        if (context.patient_phone and patient.get("phone") == context.patient_phone and
            context.caller_phone is None and context.caller_name is None and 
            context.caller_relationship is None):
            return True

        if context.caller_phone and patient.get("phone") == context.caller_phone:
            return True

        if context.patient_phone and patient.get("phone") == context.patient_phone and context.caller_name:
            if context.caller_name.lower().strip() == (patient.get("name") or "").lower().strip():
                return True

        if context.caller_phone and patient_tool.can_caller_access_patient(
            caller_identifier=None,
            patient_id=patient_id,
            patient_phone=patient.get("phone"),
            caller_phone=context.caller_phone,
        ):
            return True

        if context.caller_phone:
            for guardian in self.clinic.patients:
                if guardian.get("phone") == context.caller_phone and patient_id in (guardian.get("guardian_of") or []):
                    return True

        if context.caller_name:
            caller_name = context.caller_name.lower().strip()
            patient_name = (patient.get("name") or "").lower().strip()
            if caller_name == patient_name:
                return True

        return False

    def _find_appointment(
        self,
        patient_id: str,
        appointment_id: Optional[str] = None,
        date: Optional[str] = None,
        time: Optional[str] = None,
        doctor_id: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        if appointment_id:
            appointment = self.clinic.get_appointment(appointment_id)
            if appointment and appointment.get("patient_id") == patient_id:
                return appointment
            return None

        appointments = [apt for apt in self.clinic.get_patient_appointments(patient_id) if apt.get("status") in ("booked", "confirmed")]
        if date:
            appointments = [apt for apt in appointments if apt.get("date") == date]
        if time:
            appointments = [apt for apt in appointments if apt.get("start") == time]
        if doctor_id:
            appointments = [apt for apt in appointments if apt.get("doctor_id") == doctor_id]
        if len(appointments) == 1:
            return appointments[0]
        return None

    def _escalate(
        self,
        conversation_id: str,
        reason: str,
        turns: int,
        tokens: int,
        reply: str,
        existing_calls: Optional[List[ToolCall]] = None,
    ) -> AgentResponse:
        tool_calls = list(existing_calls or [])
        result = escalation_tool.escalate_to_human(reason)
        if result.get("success"):
            tool_calls.append(ToolCall(name="escalate_to_human", arguments={"reason": reason}))
            return self._build_response(
                conversation_id,
                "escalated",
                reply,
                turns,
                escalation_reason=reason,
                tokens=tokens,
                tool_calls=tool_calls,
            )
        return self._build_response(
            conversation_id,
            "abandoned",
            reply,
            turns,
            tokens=tokens,
            tool_calls=tool_calls,
        )

    def _build_response(
        self,
        conversation_id: str,
        terminal_state: str,
        reply: str,
        turns: int,
        patient_id: Optional[str] = None,
        appointment_id: Optional[str] = None,
        escalation_reason: Optional[str] = None,
        tool_calls: Optional[List[ToolCall]] = None,
        tokens: int = 0,
    ) -> AgentResponse:
        return AgentResponse(
            conversation_id=conversation_id,
            tool_calls=tool_calls or [],
            terminal_state=terminal_state,
            escalation_reason=escalation_reason,
            patient_id=patient_id,
            appointment_id=appointment_id,
            reply=reply,
            metrics=Metrics(turns=turns, tokens=tokens, latency_ms=0),
        )

    def _reset_clinic_state(self):
        import app.services.clinic_data as clinic_data_module
        clinic_data_module._clinic_data = clinic_data_module.ClinicData()

    @staticmethod
    def _normalise_turns(turns: List[Any]) -> List[str]:
        result: List[str] = []
        for item in turns:
            # Objects from different clients may have 'text' or 'content'
            if hasattr(item, "text"):
                result.append(str(item.text))
            elif isinstance(item, dict):
                if "text" in item:
                    result.append(str(item["text"]))
                elif "content" in item:
                    result.append(str(item["content"]))
                else:
                    # Fallback: stringify the dict so nothing is silently dropped
                    result.append(json.dumps(item))
            else:
                result.append(str(item))
        return result

    @staticmethod
    def _clean_json(raw: str) -> str:
        text = raw.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            return text[start : end + 1]
        return text

    @staticmethod
    def _is_availability_only_request(turns: List[str]) -> bool:
        """
        Detect if the user is asking for availability info only, not explicitly booking.
        Looks at the full conversation to determine intent.
        """
        if not turns:
            return False
        
        # Combine all text and look for patterns
        full_text = " ".join(turns).lower()
        
        # Patterns indicating availability inquiry only
        availability_keywords = [
            r"\bwhat\b.*\b(slot|time|available|free)",
            r"\bavailable\b.*\b(slot|time)",
            r"\bshow\b.*\b(slot|time|available)",
            r"\b(slot|time).*\bavailable",
            r"\bfree\b.*\btime",
            r"\bwhen\b.*\b(free|available|slot)",
            r"\bkab\b.*\b(khali|available)",  # Hindi: when + free/available
        ]
        
        # Patterns indicating booking/confirmation
        booking_keywords = [
            r"\bbook\b",
            r"\bconfirm\b",
            r"\bselect\b",
            r"\bschedule\b",
            r"\bat\b\s+\d{1,2}",  # "at 9 AM" pattern
            r"\bappoint",
        ]
        
        # Check if there's explicit booking language
        for pattern in booking_keywords:
            if re.search(pattern, full_text):
                return False
        
        # Check if it's asking for availability
        for pattern in availability_keywords:
            if re.search(pattern, full_text):
                return True
        
        return False

    @staticmethod
    def _normalise_phone(value: Any) -> Optional[str]:
        if value is None:
            return None
        digits = re.sub(r"\D", "", str(value))
        if re.fullmatch(r"\d{10}", digits):
            return digits
        return None

    @staticmethod
    def _normalise_name(value: Any) -> Optional[str]:
        if value is None:
            return None
        name = str(value).strip()
        return name or None

    @staticmethod
    def _normalise_time(value: Any) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip().lower()
        if not text:
            return None

        word_map = {
            "nau": "09:00",
            "9": "09:00",
            "10": "10:00",
            "das": "10:00",
            "dus": "10:00",
            "11": "11:00",
            "gyarah": "11:00",
            "12": "12:00",
            "baarah": "12:00",
            "barah": "12:00",
            "saadhe nau": "09:30",
            "saadhenau": "09:30",
            "9:30": "09:30",
            "9:00": "09:00",
            "10:00": "10:00",
            "11:00": "11:00",
            "12:00": "12:00",
        }
        if text in word_map:
            return word_map[text]

        match = re.fullmatch(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text)
        if not match:
            return None
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        meridian = match.group(3)
        if meridian == "pm" and hour < 12:
            hour += 12
        if meridian == "am" and hour == 12:
            hour = 0
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return f"{hour:02d}:{minute:02d}"
        return None

    @staticmethod
    def _normalise_date(value: Any, today: str) -> Optional[str]:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        try:
            datetime.strptime(text, "%Y-%m-%d")
            return text
        except ValueError:
            pass
        result = parse_date_string(text, today)
        return result

    @staticmethod
    def _doctor_id(name: Optional[str]) -> Optional[str]:
        if not name:
            return None
        text = name.lower()
        if "rao" in text:
            return "dr_rao"
        if "sethi" in text:
            return "dr_sethi"
        return None

    @staticmethod
    def _is_unsupported_request(turns: List[str]) -> bool:
        text = " ".join(turns).lower()
        unsupported_phrases = [
            "cancel all",
            "cancel every",
            "bulk cancel",
            "delete all appointments",
            "delete every appointment",
            "admin mode",
            "administrator",
            "all patients",
            "all appointments",
            "export data",
            "send report",
            "reset system",
        ]
        return any(phrase in text for phrase in unsupported_phrases)

    def _fallback_context(self, turns: List[str], today: str) -> ConversationContext:
        context = ConversationContext()
        text = " ".join(turns).lower()

        if "cancel" in text or "रद्द" in text:
            context.intent = "cancel"
        elif "reschedule" in text or "change appointment" in text or "shift" in text:
            context.intent = "reschedule"
        elif "appointment" in text or "doctor" in text or "dr." in text:
            context.intent = "book"
        else:
            context.intent = "abandon"

        if "rao" in text:
            context.doctor_name = "Rao"
            context.doctor_id = "dr_rao"
        elif "sethi" in text:
            context.doctor_name = "Sethi"
            context.doctor_id = "dr_sethi"

        # Accept any 10-digit phone number (not just those starting with 9)
        phones = re.findall(r"\b\d{10}\b", text)
        if phones:
            context.patient_phone = phones[-1]
            # Try to capture a name immediately before the phone if present (e.g. "Vedant Jain 6378411580")
            m = re.search(r"([A-Za-z][A-Za-z\s]{1,50})\s+" + re.escape(phones[-1]), text)
            if m:
                name = m.group(1).strip()
                # Basic normalization: collapse spaces and title-case
                name = re.sub(r"\s+", " ", name).title()
                context.patient_name = name

        if any(word in text for word in ["subah", "morning", "सुबह"]):
            context.time_preference = "subah"
        elif any(word in text for word in ["dopahar", "afternoon", "दोपहर"]):
            context.time_preference = "dopahar"
        elif any(word in text for word in ["shaam", "evening", "शाम"]):
            context.time_preference = "shaam"

        return context