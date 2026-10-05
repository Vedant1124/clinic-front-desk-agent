# Clinic Front Desk Agent

A conversational AI agent for handling common clinic front-desk workflows such as appointment booking, rescheduling, cancellation, patient lookup, and appointment availability.

The system uses a React frontend, a Python FastAPI backend, an LLM for natural-language understanding, and deterministic tools for all clinic operations.

---

## Features

- Conversational appointment booking
- Appointment rescheduling
- Appointment cancellation
- Patient lookup
- Doctor and slot availability search
- Multi-turn conversation handling
- Date, time, and doctor corrections
- Patient authorization checks
- Guardian-based appointment handling
- Ambiguous patient detection
- Medical-advice escalation
- Clinical-urgent escalation
- Unsupported-request refusal
- Deterministic clinic tools
- Conversation persistence in the frontend
- Tool-call and performance metrics

---

## Tech Stack

### Backend

- Python
- FastAPI
- Pydantic
- Python Dateutil
- Groq API
- `openai/gpt-oss-20b`

### Frontend

- React
- JavaScript
- Vite
- CSS

### Storage

The project uses the provided synthetic clinic data.

No external production database is required.

---

## Project Structure

```text
Assignment/
│
├── backend/
│   ├── app/
│   ├── main/
│   ├── tests/
│   ├── venv/
│   ├── clinic.json
│   ├── requirements.txt
│   ├── run.py
│   └── schema.md
│
├── conversations/
│   ├── cv_0001.json
│   ├── cv_0002.json
│   ├── ...
│   └── cv_0015.json
│
├── results/
│
├── frontend/
│
├── runner.py
├── DECISIONS.md
├── AI_TRANSCRIPT.md
└── README.md
```

---

## Backend Setup

Navigate to the backend directory:

```powershell
cd D:\swasthik\Assignment\backend
```

Create/activate the virtual environment:

```powershell
.\venv\Scripts\activate
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create a `.env` file containing the Groq API key:

```text
GROQ_API_KEY=your_api_key_here
```

The `.env` file should not be committed to Git.

---

## Running the Backend

Start the FastAPI server:

```powershell
uvicorn app.main:app --reload
```

The backend will be available at:

```text
http://localhost:8000
```

---

## Running the Frontend

Open another terminal and navigate to the frontend:

```powershell
cd D:\swasthik\Assignment\frontend
```

Install dependencies:

```powershell
npm install
```

Start the development server:

```powershell
npm run dev
```

The frontend can then be opened using the URL shown by Vite.

---

## API

The backend exposes a single endpoint:

```text
POST /agent/run
```

### Request

```json
{
  "conversation_id": "cv_0001",
  "today": "2026-10-01",
  "turns": [
    {
      "role": "user",
      "content": "I want to book an appointment."
    }
  ]
}
```

### Response

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

---

## Agent Tools

The agent uses six deterministic tools.

### 1. `search_slots`

Searches for available appointment slots based on:

- doctor
- date
- time preference
- clinic schedule
- doctor leave
- holidays
- existing appointments

The tool never invents availability.

---

### 2. `book_appointment`

Creates an appointment using an available slot.

The appointment is created only after:

- patient identification
- authorization checks where required
- doctor/date/time validation
- availability verification

---

### 3. `reschedule_appointment`

Moves an existing appointment to another available slot.

The existing appointment and patient must be identified before the operation.

---

### 4. `cancel_appointment`

Cancels an existing appointment after validating the patient and caller authorization.

---

### 5. `lookup_patient`

Searches the synthetic patient database using available identity information.

If multiple patients match, the system does not guess.

---

### 6. `escalate_to_human`

Escalates cases that require human intervention.

Examples include:

- ambiguous patient
- unauthorized operation
- medical advice
- urgent clinical symptoms
- unsupported requests

---

## Safety Rules

The system follows strict safety rules.

### Ambiguous Patient

If multiple patients match the supplied information, the system does not select one arbitrarily.

The conversation is escalated with:

```text
ambiguous_patient
```

---

### Authorization

Operations performed on behalf of another patient require appropriate authorization.

Unauthorized requests are escalated with:

```text
not_authorised
```

---

### Medical Advice

The agent does not provide medical advice.

Requests involving medication or treatment recommendations are escalated with:

```text
medical_advice
```

---

### Clinical Urgency

If the caller describes potentially urgent symptoms, the scheduling workflow stops immediately.

The case is escalated with:

```text
clinical_urgent
```

No appointment is booked after the urgent condition is detected.

---

### Unsupported Requests

Requests outside the supported clinic workflow are refused.

Examples:

- cancel every appointment
- administrator mode
- bulk operations
- exporting clinic data
- resetting the system

---

## Multi-Turn Conversations

The agent maintains context throughout a conversation.

The latest correction overrides previously extracted information.

For example:

```text
User: Book Dr Rao on October 6.
User: Actually, October 7.
```

The final booking uses October 7.

The same approach is used for:

- doctor corrections
- date corrections
- time corrections
- patient information corrections

---

## Availability-Only Requests

The system distinguishes between searching for availability and actually booking an appointment.

For example:

```text
What slots are available with Dr Rao on October 3?
```

will search available slots without creating an appointment.

---

## Determinism

The LLM is configured with temperature `0`.

The clinic data is fixed and synthetic.

The deterministic tool layer ensures that clinic state is not generated by the LLM.

The same conversation is expected to produce the same:

- terminal state
- escalation reason
- set of tool names

across repeated runs.

---

## Testing

The implementation was tested against all 15 provided conversation scenarios.

The test scenarios cover:

1. Straightforward booking
2. Date correction
3. Rescheduling
4. Cancellation
5. Abandoned availability request
6. Multi-turn booking correction
7. Ambiguous patient
8. Guardian booking
9. Unauthorized cancellation
10. Medical advice
11. Clinical urgency
12. Natural-language date interpretation
13. Unusable input
14. Unsupported administrative request
15. Time correction

### Result

```text
15 / 15 test cases passed
```

---

## Adversarial Testing

Eight adversarial conversation scripts were also tested.

The adversarial cases cover:

- Ambiguous patients
- Unauthorized requests
- Medical advice
- Clinical urgency
- Unsupported requests
- Availability-only requests
- Abandoned conversations
- Prompt injection

Command:

```powershell
python runner.py --dir adversarial --out adversarial_results
```

Result:

```text
8 scripts
failures: 0
```

---

## Metrics

The backend records performance information for conversations, including token usage and latency.

These metrics are included in the API response:

```json
{
  "metrics": {
    "turns": 0,
    "tokens": 0,
    "latency_ms": 0
  }
}
```

The metrics track:

- Conversation turns
- LLM tokens used
- Request latency in milliseconds

---

## Frontend

The React frontend provides:

- Handoff Queue
- Conversation Detail
- New Conversation
- Conversation history
- Agent responses
- Tool execution results
- Terminal outcome

Completed conversations are stored in browser local storage so they remain available in the interface.

---

## Data

The project uses synthetic clinic data supplied with the assignment.

The dataset contains:

- clinic information
- doctors
- specialties
- working hours
- holidays
- doctor leave
- patients
- patient relationships
- appointments

No real patient information is used.

---

## Design Principle

The core design principle is:

> The LLM interprets the conversation, while deterministic tools control clinic state.

The LLM is responsible for understanding natural language and extracting structured information.

The deterministic tools are responsible for:

- checking availability
- identifying patients
- validating authorization
- creating appointments
- rescheduling appointments
- cancelling appointments
- escalating cases

This separation prevents hallucinated clinic data and makes the workflow easier to test and reason about.

---

## Conclusion

The Clinic Front Desk Agent provides a conversational interface for common clinic front-desk workflows while keeping all clinic operations grounded in deterministic tools.

It supports appointment booking, rescheduling, cancellation, patient lookup, and availability search while escalating ambiguous, unauthorized, medically sensitive, and clinically urgent requests to human support.
