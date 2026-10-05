import React, { useEffect, useRef, useState } from "react";

const API_URL = "https://clinic-front-desk-agent-4.onrender.com/agent/run";

function StatusBadge({ status }) {
  const value = status || "UNKNOWN";

  return (
    <span
      className={`status-badge ${value
        .toLowerCase()
        .replaceAll("_", "-")}`}
    >
      {value.replaceAll("_", " ")}
    </span>
  );
}

function Sidebar({ page, setPage }) {
  return (
    <aside className="sidebar">
      <div className="brand">
        <div className="brand-icon">✚</div>
        <div>
          <div className="brand-title">Clinic Front Desk</div>
          <div className="brand-subtitle">Agent Console</div>
        </div>
      </div>

      <div className="nav-section">
        <div className="nav-title">WORKSPACE</div>

        <button
          className={`nav-item ${page === "queue" ? "active" : ""}`}
          onClick={() => setPage("queue")}
        >
          <span>▦</span>
          Handoff Queue
        </button>

        <button
          className={`nav-item ${page === "detail" ? "active" : ""}`}
          onClick={() => setPage("detail")}
        >
          <span>▤</span>
          Conversation Detail
        </button>
      </div>

      <div className="sidebar-footer">
        <div className="online-dot" />
        Agent Online
      </div>
    </aside>
  );
}

function ChatMessage({ message }) {
  const isUser = message.role === "user";

  return (
    <div className={`message-row ${isUser ? "caller" : "agent"}`}>
      <div className="message">
        <div className="message-label">
          {isUser ? "CALLER" : "AGENT"}
        </div>
        <div className="message-text">{message.content}</div>
      </div>
    </div>
  );
}

function ToolCallCard({ tool }) {
  return (
    <div className="tool-card">
      <div className="tool-header">
        <span className="tool-icon">⚙</span>
        <span>{tool.name}</span>
      </div>

      {tool.arguments && (
        <pre>{JSON.stringify(tool.arguments, null, 2)}</pre>
      )}
    </div>
  );
}

function OutcomePanel({ response }) {
  if (!response) {
    return (
      <div className="outcome-empty">
        <div className="empty-symbol">◌</div>
        <h3>No outcome yet</h3>
        <p>Conversation outcome will appear here.</p>
      </div>
    );
  }

  return (
    <div className="outcome-panel">
      <div className="panel-title">Outcome</div>

      <div className="outcome-status">
        <span>Terminal State</span>
        <StatusBadge status={response.terminalState} />
      </div>

      <div className="details">
        <Detail
          label="Escalation Reason"
          value={response.escalationReason}
        />
        <Detail label="Patient ID" value={response.patientId} />
        <Detail
          label="Appointment ID"
          value={response.appointmentId}
        />
        <Detail label="Tool Calls" value={response.toolCallsCount} />
        <Detail label="Turns" value={response.turns} />
        <Detail label="Tokens" value={response.tokens} />
        <Detail label="Latency" value={response.latency} />
        <Detail label="Determinism" value={response.determinism} />
      </div>

      {response.toolCalls?.length > 0 && (
        <div className="tools-section">
          <div className="section-title">Tool Calls</div>

          {response.toolCalls.map((tool, index) => (
            <ToolCallCard key={index} tool={tool} />
          ))}
        </div>
      )}
    </div>
  );
}

function Detail({ label, value }) {
  return (
    <div className="detail-row">
      <span>{label}</span>
      <strong>
        {value === null || value === undefined || value === ""
          ? "—"
          : String(value)}
      </strong>
    </div>
  );
}

function QueuePage({ conversations, openConversation }) {
  const completedCount = conversations.filter(
    (c) =>
      c.response?.terminalState !== "escalated" &&
      c.response?.terminalState !== "refused"
  ).length;

  const escalatedCount = conversations.filter(
    (c) => c.response?.terminalState === "escalated"
  ).length;

  const urgentCount = conversations.filter(
    (c) => c.response?.escalationReason === "clinical_urgent"
  ).length;

  return (
    <main className="page">
      <header className="page-header">
        <div>
          <h1>Handoff Queue</h1>
          <p>Review conversations that need human attention.</p>
        </div>

        <div className="clinic-pill">
          Sunrise Clinic · Dehradun
        </div>
      </header>

      <div className="stats">
        <StatCard
          label="Conversations"
          value={conversations.length}
        />

        <StatCard
          label="Completed by Agent"
          value={completedCount}
        />

        <StatCard
          label="Escalated"
          value={escalatedCount}
        />

        <StatCard
          label="Urgent"
          value={urgentCount}
          urgent
        />
      </div>

      <section className="queue-card">
        <div className="queue-header">
          <div>
            <h2>Conversations</h2>
            <p>All conversations handled by the agent</p>
          </div>

          <span className="count-badge">
            {conversations.length} conversations
          </span>
        </div>

        {conversations.length === 0 ? (
          <div className="empty-queue">
            <div className="empty-symbol">◌</div>
            <h3>No conversations yet</h3>
            <p>
              Start a conversation from the Conversation Detail
              page.
            </p>
          </div>
        ) : (
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Conversation</th>
                  <th>Caller Said</th>
                  <th>Outcome</th>
                  <th>Time</th>
                  <th>View</th>
                </tr>
              </thead>

              <tbody>
                {[...conversations].reverse().map((item) => {
                  const firstUserMessage = item.turns?.find(
                    (turn) => turn.role === "user"
                  );

                  const terminalState =
                    item.response?.terminalState || "unknown";

                  return (
                    <tr key={item.id}>
                      <td>
                        <button
                          className="conversation-link"
                          onClick={() =>
                            openConversation(item.id)
                          }
                        >
                          {item.id}
                        </button>
                      </td>

                      <td className="caller-preview">
                        {firstUserMessage?.content ||
                          "Conversation"}
                      </td>

                      <td>
                        <StatusBadge status={terminalState} />
                      </td>

                      <td className="muted">
                        {item.time || "—"}
                      </td>

                      <td>
                        <button
                          className="resolve-btn"
                          onClick={() =>
                            openConversation(item.id)
                          }
                        >
                          View
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </main>
  );
}

function StatCard({ label, value, urgent }) {
  return (
    <div className={`stat-card ${urgent ? "urgent-card" : ""}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
    </div>
  );
}

function ConversationPage({
  turns,
  input,
  setInput,
  sendMessage,
  loading,
  response,
  chatRef,
  conversationId,
}) {
  return (
    <main className="page conversation-page">
      <header className="conversation-header">
        <div>
          <div className="eyebrow">CONVERSATION DETAIL</div>

          <h1>{conversationId}</h1>

          <div className="header-meta">
            Sunrise Clinic · Dehradun
          </div>
        </div>

        {response?.terminalState && (
          <StatusBadge status={response.terminalState} />
        )}
      </header>

      <div className="conversation-layout">
        <section className="chat-card">
          <div className="chat-header">
            <div>
              <strong>Conversation</strong>
              <span>Live agent interaction</span>
            </div>
          </div>

          <div className="chat-body" ref={chatRef}>
            {turns.length === 0 ? (
              <div className="empty-chat">
                <div className="empty-symbol">◯</div>

                <h3>Start a conversation</h3>

                <p>
                  Type a message below to interact with the
                  clinic front desk agent.
                </p>
              </div>
            ) : (
              turns.map((turn, index) => (
                <ChatMessage
                  key={index}
                  message={turn}
                />
              ))
            )}

            {loading && (
              <div className="message-row agent">
                <div className="message loading-message">
                  <div className="message-label">AGENT</div>

                  <div className="typing">
                    <span />
                    <span />
                    <span />
                  </div>
                </div>
              </div>
            )}
          </div>

          <div className="composer">
            <textarea
              value={input}
              disabled={loading}
              placeholder="Type a message..."
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (
                  e.key === "Enter" &&
                  !e.shiftKey
                ) {
                  e.preventDefault();
                  sendMessage();
                }
              }}
            />

            <button
              className="send-btn"
              disabled={loading || !input.trim()}
              onClick={sendMessage}
            >
              Send
            </button>
          </div>
        </section>

        <aside className="outcome-card">
          <OutcomePanel response={response} />
        </aside>
      </div>
    </main>
  );
}

export default function App() {
  const [page, setPage] = useState("queue");

  const [conversationId, setConversationId] = useState(
    () => `cv_${Date.now()}`
  );

  const [today] = useState("2026-10-01");

  const [turns, setTurns] = useState([]);

  const [input, setInput] = useState("");

  const [loading, setLoading] = useState(false);

  const [response, setResponse] = useState(null);

  const [conversations, setConversations] = useState(() => {
    const saved = localStorage.getItem(
      "clinic_conversations"
    );

    return saved ? JSON.parse(saved) : [];
  });

  const chatRef = useRef(null);

  const saveConversation = (
    id,
    conversationTurns,
    conversationResponse
  ) => {
    const conversation = {
      id,
      turns: conversationTurns,
      response: conversationResponse,
      time: new Date().toLocaleTimeString([], {
        hour: "2-digit",
        minute: "2-digit",
      }),
    };

    setConversations((previous) => {
      const updated = [
        ...previous.filter((item) => item.id !== id),
        conversation,
      ];

      localStorage.setItem(
        "clinic_conversations",
        JSON.stringify(updated)
      );

      return updated;
    });
  };

  const sendMessage = async () => {
    if (!input.trim() || loading) return;

    const newTurns = [
      ...turns,
      {
        role: "user",
        content: input.trim(),
      },
    ];

    setTurns(newTurns);
    setInput("");
    setLoading(true);

    try {
      const start = Date.now();

      const resp = await fetch(API_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          conversation_id: conversationId,
          today,
          turns: newTurns.map(
            (turn) => turn.content
          ),
        }),
      });

      const latency = Date.now() - start;

      if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      }

      const data = await resp.json();

      const agentTurn = {
        role: "agent",
        content: data.reply || "",
      };

      const updatedTurns = [
        ...newTurns,
        agentTurn,
      ];

      setTurns(updatedTurns);

      const conversationResponse = {
        terminalState: data.terminal_state,
        escalationReason: data.escalation_reason,
        patientId: data.patient_id,
        appointmentId: data.appointment_id,
        toolCalls: data.tool_calls || [],
        toolCallsCount:
          (data.tool_calls || []).length,
        turns: newTurns.length,
        tokens: data.tokens_used,
        latency: `${latency} ms`,
        determinism: data.determinism,
      };

      setResponse(conversationResponse);

      saveConversation(
        conversationId,
        updatedTurns,
        conversationResponse
      );
    } catch (error) {
      const errorTurn = {
        role: "agent",
        content: `Error: ${error.message}`,
      };

      setTurns((previous) => [
        ...previous,
        errorTurn,
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (chatRef.current) {
      chatRef.current.scrollTop =
        chatRef.current.scrollHeight;
    }
  }, [turns, loading]);

  const openConversation = (id) => {
    const selected = conversations.find(
      (item) => item.id === id
    );

    if (!selected) return;

    setConversationId(selected.id);
    setTurns(selected.turns || []);
    setResponse(selected.response || null);
    setPage("detail");
  };

  const startNewConversation = () => {
    const newId = `cv_${Date.now()}`;

    setConversationId(newId);
    setTurns([]);
    setResponse(null);
    setInput("");
    setPage("detail");
  };

  return (
    <div className="app">
      <Sidebar
        page={page}
        setPage={setPage}
      />

      <div className="main">
        {page === "queue" ? (
          <QueuePage
            conversations={conversations}
            openConversation={openConversation}
          />
        ) : (
          <ConversationPage
            turns={turns}
            input={input}
            setInput={setInput}
            sendMessage={sendMessage}
            loading={loading}
            response={response}
            chatRef={chatRef}
            conversationId={conversationId}
          />
        )}
      </div>

      {page === "queue" && (
        <button
          className="floating-new-btn"
          onClick={startNewConversation}
        >
          + New Conversation
        </button>
      )}
    </div>
  );
}
