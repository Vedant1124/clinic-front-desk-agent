# AI Transcript

## 1. Project Planning

The initial objective was to build a Clinic Front Desk Agent capable of handling common clinic workflows through a conversational interface.

The main requirements identified were:

- appointment booking
- appointment rescheduling
- appointment cancellation
- patient lookup
- slot availability
- authorization
- escalation
- multi-turn conversation handling
- deterministic behavior
- React frontend
- Python REST backend

The implementation was planned around a separation between natural-language understanding and deterministic clinic operations.

---

## 2. Architecture Decision

The project was structured into:

```text
React Frontend
       |
       v
FastAPI REST API
       |
       v
Conversational Agent
       |
       +-------------------+
       |                   |
       v                   v
      LLM          Deterministic Tools
                           |
                           v
                    Clinic Data
```

The LLM interprets the conversation, while the tool layer performs actual clinic operations.

This prevents the LLM from directly modifying clinic state.

---

## 3. Backend Implementation

The backend was implemented using Python and FastAPI.

The required API endpoint was:

```text
POST /agent/run
```

The endpoint receives:

- conversation ID
- current date
- conversation turns

and returns:

- tool calls
- terminal state
- escalation reason
- patient ID
- appointment ID
- response
- metrics

---

## 4. LLM Integration

The conversational agent uses:

```text
openai/gpt-oss-20b
```

through Groq.

The model is used primarily for:

- intent detection
- extracting patient information
- extracting doctor information
- extracting dates
- extracting times
- understanding caller relationships
- understanding corrections across multiple turns

The model is configured with temperature `0` to improve deterministic behavior.

The LLM does not directly create or modify appointments.

---

## 5. Deterministic Tools

Six tools were implemented:

```text
search_slots
book_appointment
reschedule_appointment
cancel_appointment
lookup_patient
escalate_to_human
```

The tools operate against the synthetic clinic data.

The tools do not call an LLM.

This ensures that clinic state remains grounded in the supplied dataset.

---

## 6. Patient Lookup

Patient lookup was designed to avoid guessing.

The lookup process uses information such as:

- patient name
- phone number
- date of birth

If one patient matches, the patient can be selected.

If multiple patients match, the system escalates instead of guessing.

This was particularly important for names such as:

```text
Sharma
Gupta
```

where multiple patients may exist.

---

## 7. Authorization

Authorization was added for operations involving another patient.

The system checks caller information and configured patient relationships before allowing operations such as cancellation or rescheduling.

If authorization cannot be established, the agent uses:

```text
not_authorised
```

and does not modify the appointment.

Guardian relationships in the synthetic dataset are also supported.

---

## 8. Clinical Safety

A safety-first approach was implemented.

The agent does not provide medical advice.

Requests involving medication or treatment recommendations result in:

```text
medical_advice
```

Potentially urgent symptoms are handled immediately using:

```text
clinical_urgent
```

The normal scheduling workflow is stopped when an urgent clinical situation is detected.

---

## 9. Multi-Turn Context

The agent was designed to retain information across turns.

For example:

```text
User:
Book an appointment with Dr Rao on October 6.

User:
Actually, October 7.
```

The final request is interpreted as October 7.

The same approach is applied to:

- doctor corrections
- date corrections
- time corrections
- patient information corrections

The latest explicit correction takes precedence.

---

## 10. Availability Handling

The `search_slots` tool was implemented as the source of truth for appointment availability.

The search takes into account:

- doctor schedule
- working days
- holidays
- doctor leave
- existing appointments
- slot duration

The agent does not invent available slots.

---

## 11. Availability-Only Bug

During testing, an issue was identified where a conversation asking only for available slots could result in a booking.

The logic was updated to distinguish between:

```text
availability search
```

and:

```text
actual booking request
```

Availability-only requests now perform a slot search without creating an appointment.

---

## 12. Multi-Turn Correction Testing

Multi-turn conversations were tested with changes such as:

```text
Dr Rao
    ->
Dr Sethi
```

and:

```text
October 6
    ->
October 7
```

The final operation uses the latest corrected information.

This was important for the provided test cases involving doctor and date corrections.

---

## 13. Ambiguous Patient Testing

An ambiguous patient scenario was tested using a partial/common name.

The system initially required improvement to correctly detect multiple possible patients.

The patient resolution logic was updated so that matching is based on available identity information rather than hardcoding a specific name.

The final behavior correctly escalates ambiguous cases with:

```text
ambiguous_patient
```

---

## 14. Unauthorized Operation Testing

An unauthorized cancellation scenario was tested where the caller was not authorized to cancel the patient's appointment.

The system correctly:

1. looked up the patient
2. checked authorization
3. rejected the operation
4. escalated with `not_authorised`

No cancellation was performed.

---

## 15. Medical Advice Testing

A conversation involving fever, medication, and dosage/duration advice was tested.

The system correctly identified that the request required medical advice and escalated with:

```text
medical_advice
```

No appointment operation was performed.

---

## 16. Clinical Urgency Testing

A conversation initially involving appointment scheduling was followed by urgent symptoms such as chest pain and shortness of breath.

The system was designed to check urgent clinical information before continuing the scheduling workflow.

The final result was:

```text
clinical_urgent
```

No booking was created.

---

## 17. Unsupported Request Testing

Administrative or unsafe bulk requests were tested.

Examples included requests such as:

```text
cancel every appointment
```

and attempts to enter an administrator mode.

These requests are refused without executing clinic operations.

---

## 18. Abandoned Conversation Handling

The system was tested with a user who requested available slots but then decided to call later.

The expected behavior was:

```text
abandoned
```

No appointment was created.

This prevents the agent from treating an availability request as implicit booking authorization.

---

## 19. Frontend Implementation

A React frontend was added to provide a conversational interface.

The frontend includes:

- Handoff Queue
- Conversation Detail
- New Conversation
- conversation history
- agent responses
- terminal outcomes

Conversation history is stored in browser local storage.

The frontend communicates with the backend using:

```text
POST /agent/run
```

---

## 20. Frontend Iteration

The initial frontend contained a separate conversation navigation section.

It was simplified so that the primary interface focuses on:

```text
Handoff Queue
Conversation Detail
```

A new conversation action was also added.

Existing conversations are stored and can be reopened from the Handoff Queue.

---

## 21. Testing the Complete Assignment

The implementation was tested against all 15 provided conversation cases.

The cases covered:

- normal booking
- date correction
- rescheduling
- cancellation
- availability-only request
- abandoned conversation
- ambiguous patient
- guardian booking
- unauthorized cancellation
- medical advice
- urgent symptoms
- natural-language date handling
- unusable input
- unsupported administrative request
- time correction

Final result:

```text
15 / 15 test cases passed
```

---

## 22. Determinism Testing

The assignment requires deterministic behavior across repeated runs.

The implementation uses:

```text
temperature = 0
```

and deterministic clinic tools.

The same conversations were tested repeatedly to verify consistency of:

- terminal state
- escalation reason
- tool set

---

## 23. Documentation

The project documentation was created to explain:

- architecture
- design decisions
- safety rules
- deterministic tool layer
- patient identification
- authorization
- testing
- frontend
- LLM usage
- performance metrics

The following documentation files were added:

```text
README.md
DECISIONS.md
AI_TRANSCRIPT.md
```

---

## 24. Final Result

The completed system provides a conversational clinic front-desk workflow with:

- natural-language understanding
- deterministic clinic operations
- patient identity validation
- authorization checks
- appointment management
- safety escalation
- multi-turn corrections
- React frontend
- conversation persistence
- deterministic testing

The final implementation successfully passed all 15 provided conversation scenarios.