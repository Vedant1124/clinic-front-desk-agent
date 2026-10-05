# DECISIONS.md

## 1. Architecture

The system is divided into three main layers:

- **Frontend:** React-based conversational interface for clinic staff.
- **Backend:** Python REST API built using FastAPI.
- **Tool Layer:** Deterministic clinic operations such as patient lookup, slot search, booking, rescheduling, cancellation, and escalation.

The frontend communicates with the backend through a single REST endpoint:

```text
POST /agent/run
```

This keeps the interface simple while allowing the backend agent to manage the complete conversation workflow.

---

## 2. LLM Choice

The agent uses:

```text
openai/gpt-oss-20b
```

through the Groq API.

The LLM is responsible for understanding the user's natural-language request and extracting structured information such as:

- patient name
- patient phone number
- caller information
- doctor
- date
- time
- intent
- requested corrections

The LLM does **not** directly modify clinic data.

All actual clinic operations are performed through deterministic tools.

---

## 3. Deterministic Tool Layer

All clinic operations are implemented as deterministic tools.

The available tools are:

- `search_slots`
- `book_appointment`
- `reschedule_appointment`
- `cancel_appointment`
- `lookup_patient`
- `escalate_to_human`

The tools do not call the LLM.

They operate only on the clinic's synthetic data and return grounded results.

This prevents the agent from inventing:

- patients
- appointments
- doctors
- available slots
- booking confirmations

---

## 4. Patient Identification

Patient identification is performed using available patient information such as:

- name
- phone number
- date of birth where applicable

If exactly one patient matches the supplied information, that patient is selected.

If multiple patients match, the system does not guess.

Instead, the conversation is escalated with:

```text
ambiguous_patient
```

This is particularly important for common names such as Sharma or Gupta.

---

## 5. Authorization

The system distinguishes between the patient and the person calling on their behalf.

For operations such as cancellation and rescheduling, authorization is checked before modifying an appointment.

Supported authorized relationships include appropriate self-identification and configured guardian relationships in the synthetic clinic data.

If the caller cannot be authorized to perform the requested operation, the agent escalates with:

```text
not_authorised
```

No appointment is modified in this case.

---

## 6. Clinical Safety

The agent does not provide medical advice.

If a user asks questions such as:

- which medicine to take
- whether a medicine should be taken
- how long to take a medicine
- treatment recommendations

the agent escalates with:

```text
medical_advice
```

If the caller describes potentially urgent symptoms, the agent immediately stops the normal scheduling workflow and escalates with:

```text
clinical_urgent
```

No appointment booking is performed after an urgent clinical situation is identified.

---

## 7. Multi-Turn Conversations

The agent maintains conversation context across turns.

Information from earlier turns is retained unless the user explicitly corrects it.

For example:

```text
Book Dr Rao on October 6.
```

followed by:

```text
Actually, October 7.
```

results in October 7 being used for the final operation.

The latest user correction takes precedence over the previous value.

The same approach is used for:

- doctor changes
- date changes
- time changes
- patient information corrections

---

## 8. Appointment Availability

Appointment availability is always checked using the deterministic `search_slots` tool.

The agent does not invent availability.

The search respects clinic configuration including:

- doctor working hours
- working days
- holidays
- doctor leave
- slot duration
- already booked appointments

If the requested slot is unavailable, the agent uses the available slots returned by the tool rather than fabricating another slot.

---

## 9. Availability-Only Requests

If the user only asks which slots are available, the agent searches the schedule but does not create an appointment.

For example:

```text
What slots are available with Dr Rao on October 3?
```

should result in a slot search without a booking operation.

A booking is only created when the caller actually requests an appointment.

---

## 10. Abandoned Conversations

If the user requests information but does not proceed with booking, the agent does not create an appointment.

For example:

```text
What slots are available?
```

followed by:

```text
I'll call later.
```

results in:

```text
abandoned
```

No appointment is created.

---

## 11. Unsupported or Unsafe Requests

The agent rejects requests that are outside the supported clinic front-desk workflow.

Examples include:

- cancelling every appointment
- bulk cancellation
- administrator-mode instructions
- exporting clinic data
- system reset requests
- other unsupported administrative operations

These requests are refused without executing clinic tools.

---

## 12. Tool Error Handling

Tool arguments are validated before clinic operations are performed.

Malformed or incomplete requests result in actionable errors instead of silent failures.

The agent does not assume missing information when it could lead to an incorrect patient, appointment, doctor, or time.

---

## 13. Determinism

The agent uses deterministic settings for LLM extraction and deterministic clinic tools.

The model temperature is set to:

```text
0
```

The clinic data is fixed and synthetic.

The same conversation is therefore expected to produce the same:

- terminal state
- escalation reason
- set of tools used

across repeated runs.

This was verified using the provided conversation test cases.

---

## 14. Conversation Persistence

The React frontend stores completed conversations locally so that previous conversations remain available in the interface.

The frontend provides:

- Handoff Queue
- Conversation Detail
- New Conversation
- conversation history
- terminal outcome information

The backend remains responsible for the actual clinic workflow and tool execution.

---

## 15. Synthetic Clinic Data

The project uses the provided synthetic clinic data.

No real patient or medical data is used.

The clinic configuration contains information such as:

- doctors
- specialties
- working hours
- leave dates
- holidays
- patients
- relationships
- appointments

All appointment operations are performed against this controlled dataset.

---

## 16. REST API Design

The backend exposes a single required endpoint:

```text
POST /agent/run
```

The request contains:

```text
conversation_id
today
turns
```

The response contains:

```text
conversation_id
tool_calls
terminal_state
escalation_reason
patient_id
appointment_id
reply
metrics
```

This follows the required assignment contract while keeping the API surface minimal.

---

## 17. Testing

The implementation was tested against all 15 provided conversation scenarios.

The scenarios cover:

- straightforward booking
- date correction
- doctor correction
- rescheduling
- cancellation
- availability-only requests
- abandoned conversations
- ambiguous patient identification
- guardian booking
- unauthorized cancellation
- medical advice
- urgent clinical symptoms
- multi-turn corrections
- unusable input
- unsupported administrative requests

All 15 provided test cases passed successfully.

---

## 18. Frontend Design

The frontend was implemented using React.

The interface focuses on two primary sections:

- **Handoff Queue:** displays saved conversations and their outcomes.
- **Conversation Detail:** displays the active conversation and agent response.

A new conversation can be started using the **New Conversation** action.

Conversation history is persisted in browser local storage for the frontend experience.

---

## 19. Key Design Principle

The main design principle is:

> The LLM interprets the conversation, while deterministic tools control clinic state.

This separation allows natural-language interaction without allowing the model to directly invent or modify clinic data.

It also makes safety checks, authorization, appointment availability, and deterministic testing easier to enforce.

---

## 20. Conclusion

The Clinic Front Desk Agent handles common clinic front-desk workflows through a conversational interface while keeping clinic operations grounded in deterministic tools.

The system supports appointment booking, rescheduling, cancellation, patient lookup, and availability search while escalating ambiguous, unauthorized, medically sensitive, and clinically urgent requests to human support.