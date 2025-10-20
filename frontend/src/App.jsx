import React, { useState } from "react";
import { callGenerateMCQ } from "./lib/api";
import { callGeneratePoints } from "./lib/api_points";

export default function App() {
  const [topic, setTopic] = useState("Indian Polity");
  const [count, setCount] = useState(5);
  const [loading, setLoading] = useState(false);
  const [mcqs, setMcqs] = useState(null);
  const [points, setPoints] = useState(null);
  const [pointsLoading, setPointsLoading] = useState(false);
  const [error, setError] = useState(null);

  async function handleGenerate(e) {
    e.preventDefault();
    setError(null);
    setMcqs(null);
    setLoading(true);

    try {
      const res = await callGenerateMCQ({ topic, count: Number(count) });
      if (res && res.result) {
        setMcqs(res.result);
      } else {
        setError("No results returned. See console for response.");
        console.log("Full response:", res);
      }
    } catch (err) {
      console.error(err);
      setError("Request failed: " + (err.message || err));
    } finally {
      setLoading(false);
    }
  }

  async function handleGeneratePoints(e) {
    if (e && e.preventDefault) e.preventDefault();
    setError(null);
    setPoints(null);
    setPointsLoading(true);
    try {
      const res = await callGeneratePoints({ topic, max_points: 8 });
      if (res && res.result) {
        setPoints(res.result);
      } else {
        setError("No points returned. See console for response.");
        console.log("Points full response:", res);
      }
    } catch (err) {
      console.error(err);
      setError("Points request failed: " + (err.message || err));
    } finally {
      setPointsLoading(false);
    }
  }

  return (
    <div style={styles.page}>
      <div style={styles.card}>
        <h1 style={styles.h1}>JKSSB — MCQ Generator</h1>

        <form onSubmit={handleGenerate} style={styles.form}>
          <label style={styles.label}>
            Topic
            <input
              style={styles.input}
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              required
            />
          </label>

          <label style={styles.label}>
            Number of questions
            <input
              type="number"
              min="1"
              max="20"
              style={styles.input}
              value={count}
              onChange={(e) => setCount(e.target.value)}
            />
          </label>

          <div style={{ display: "flex", gap: 8 }}>
            <button style={styles.btnPrimary} disabled={loading}>
              {loading ? "Generating…" : "Generate MCQs"}
            </button>

            <button
              type="button"
              style={styles.btnSecondary}
              onClick={() => {
                setTopic("");
                setCount(5);
                setMcqs(null);
                setPoints(null);
                setError(null);
              }}
            >
              Reset
            </button>

            <button
              type="button"
              style={{ ...styles.btnSecondary, marginLeft: 8 }}
              onClick={handleGeneratePoints}
              disabled={pointsLoading}
            >
              {pointsLoading ? "Generating points…" : "Get Important Points"}
            </button>
          </div>
        </form>

        {error && <div style={styles.error}>{error}</div>}

        {/* Points viewer */}
        {points && (
          <div style={{ marginTop: 12, padding: 12, background: "#fff7ed", borderRadius: 8 }}>
            <h3 style={{ margin: 0, marginBottom: 8 }}>Important points — {topic}</h3>
            <ol>
              {points.map((p) => (
                <li key={p.id} style={{ marginBottom: 8 }}>
                  <div style={{ fontWeight: 600 }}>{p.text}</div>
                  {p.mnemonic ? <div style={{ fontSize: 13, color: "#6b7280" }}>Mnemonic: {p.mnemonic}</div> : null}
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Render MCQs if present */}
        {mcqs && (
          <div style={{ marginTop: 18 }}>
            <h2 style={styles.h2}>Generated MCQs</h2>
            <ol>
              {mcqs.map((q) => (
                <li key={q.id} style={{ listStyle: "none", marginBottom: 12 }}>
                  <MCQCard question={q} />
                </li>
              ))}
            </ol>
          </div>
        )}
      </div>
    </div>
  );
}

/* MCQCard: renders one question, options, and reveal logic.
   Highlights the correct option with a green check when revealed. */
function MCQCard({ question }) {
  const [show, setShow] = useState(false);

  // backend uses answer_letter (like "A") and options array (0..3).
  const answerLetter = question.answer_letter || question.answer || question.answer_letter;
  // map letter to index: 'A' -> 0
  const correctIndex = (typeof answerLetter === "string" && answerLetter.length)
    ? answerLetter.toUpperCase().charCodeAt(0) - 65
    : null;

  return (
    <div style={styles.qCard}>
      <div style={{ fontWeight: 600 }}>{question.question}</div>

      <ul style={{ marginTop: 8, paddingLeft: 18 }}>
        {question.options.map((opt, idx) => {
          const isCorrect = show && idx === correctIndex;
          return (
            <li key={idx} style={{ marginBottom: 6, display: "flex", alignItems: "center" }}>
              <span style={{ width: 22, fontWeight: 600 }}>{String.fromCharCode(65 + idx)}.</span>
              <span style={{ flex: 1 }}>{opt}</span>
              {isCorrect && (
                <span
                  aria-hidden="true"
                  style={{ marginLeft: 10, color: "#16a34a", fontWeight: 700 }}
                  title="Correct answer"
                >
                  ✓
                </span>
              )}
            </li>
          );
        })}
      </ul>

      <div style={{ marginTop: 8, display: "flex", gap: 8, alignItems: "center" }}>
        <button
          style={styles.btnSecondary}
          onClick={() => setShow((s) => !s)}
          aria-expanded={show}
          aria-controls={`explain-${question.id}`}
        >
          {show ? "Hide answer" : "Show answer"}
        </button>

        {/* When revealed, show answer text and explanation */}
        {show && (
          <div id={`explain-${question.id}`} style={{ marginLeft: 6 }}>
            <div aria-live="polite">
              <strong>Answer:</strong> {answerLetter} — {question.answer}
            </div>
            {question.explain && (
              <div style={{ fontStyle: "italic", marginTop: 6 }}>{question.explain}</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// Simple inline styles to avoid extra CSS setup
const styles = {
  page: {
    fontFamily: "Inter, system-ui, -apple-system, 'Segoe UI', Roboto, 'Helvetica Neue', Arial",
    minHeight: "100vh",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    background: "#f5f7fb",
    padding: 16,
  },
  card: {
    width: 720,
    maxWidth: "95%",
    background: "white",
    borderRadius: 10,
    padding: 20,
    boxShadow: "0 6px 20px rgba(25, 30, 50, 0.08)",
  },
  h1: { margin: 0, marginBottom: 12, fontSize: 20 },
  h2: { margin: 0, marginBottom: 8, fontSize: 16 },
  form: { display: "grid", gap: 10, marginTop: 8 },
  label: { display: "flex", flexDirection: "column", fontSize: 13 },
  input: {
    marginTop: 6,
    padding: "8px 10px",
    fontSize: 14,
    borderRadius: 6,
    border: "1px solid #d6dbe6",
  },
  btnPrimary: {
    padding: "8px 14px",
    borderRadius: 8,
    border: "none",
    background: "#2563eb",
    color: "white",
    cursor: "pointer",
  },
  btnSecondary: {
    padding: "8px 14px",
    borderRadius: 8,
    border: "1px solid #cbd5e1",
    background: "white",
    cursor: "pointer",
  },
  qCard: {
    padding: 12,
    borderRadius: 8,
    background: "#fbfcff",
    border: "1px solid #eef2ff",
  },
  explain: { marginTop: 6, color: "#374151" },
  error: { marginTop: 12, color: "white", background: "#ef4444", padding: 8, borderRadius: 6 },
};
