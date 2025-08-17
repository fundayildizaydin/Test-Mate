import React, { useMemo, useState } from "react";
import "./App.css";

type GenerateResponse = {
  test_code?: string;
  error?: string;
  raw?: unknown;
};

const BACKEND_URL =
  (import.meta as any).env?.VITE_BACKEND_URL || "http://localhost:8000";

const SAMPLE_CODE = `def calculate_simple_interest(principal, interest_rate, years):
    """
    Simple interest calculation method.
    
    Parameters:
    principal (float): The initial amount of money
    interest_rate (float): Annual interest rate (as a percentage, e.g., 10 for 10%)
    years (int): Number of years
    
    Returns:
    float: Total amount (principal + interest)
    """
    interest = principal * (interest_rate / 100) * years
    total = principal + interest
    return total`;


export default function App() {    
  const [copied, setCopied] = useState(false);
  const [code, setCode] = useState<string>(SAMPLE_CODE);
  const [testCode, setTestCode] = useState<string>("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canGenerate = useMemo(
    () => code.trim().length > 0 && !loading,
    [code, loading]
  );

  async function generate() {
    setLoading(true);
    setError(null);
    setTestCode("");
    try {
      const res = await fetch(`${BACKEND_URL.replace(/\/$/, "")}/generate-test`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ code }),
      });
      const data: GenerateResponse = await res.json();
      if (!res.ok || data.error) {
        setError(data.error || `HTTP ${res.status}`);
        return;
      }
      setTestCode(data.test_code || "");
    } catch (e: any) {
      setError(e?.message || String(e));
    } finally {
      setLoading(false);
    }
  }

  async function copy(text: string) {
  try {
    if (!text) return;

    if (typeof navigator !== "undefined" &&
        navigator.clipboard &&
        window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return true;
    }

    const ta = document.createElement("textarea");
    ta.value = text;
    ta.style.position = "fixed";
    ta.style.left = "-9999px";
    ta.style.top = "0";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();

    const ok = document.execCommand("copy");
    document.body.removeChild(ta);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000); 
    if (!ok) throw new Error("Copy command failed");
    return true;
  } catch (err) {
    console.error("Copy failed:", err);
    return false;
  }
}

  function download(filename: string, content: string) {
    const blob = new Blob([content], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    const isCmdOrCtrl = e.metaKey || e.ctrlKey;
    if (isCmdOrCtrl && e.key === "Enter" && canGenerate) {
      e.preventDefault();
      generate();
    }
  }

  return (
    <div className="wrap">
      <header className="topbar">
        <div className="brand">
          <span className="logo-dot" />
          <span>Test Mate</span>
        </div>
      </header>

      {copied && (
        <div className="banner copied">
          Copied to clipboard
        </div>
      )}

      {error && (
        <div className="banner error">
          <span>⚠️ {error}</span>
          <button className="link" onClick={() => setError(null)}>
            Dismiss
          </button>
        </div>
      )}

      <main className="grid">
        {/* Left: source code */}
        <section className="panel">
          <div className="panel-head">
            <h2>Source Code</h2>
            <div className="tools">
              <button className="btn ghost" onClick={() => setCode(SAMPLE_CODE)}>
                Load sample
              </button>
              <button className="btn ghost" onClick={() => setCode("")}>
                Clear
              </button>
              <button className="btn ghost" onClick={() => copy(code)} disabled={!code.trim()}>
                Copy
              </button>
              <button
                className="btn ghost"
                onClick={() => download("under_test.py", code)} disabled={!code.trim()}
              >
                Download.py
              </button>
            </div>
          </div>

          <textarea
            className="editor"
            value={code}
            onChange={(e) => setCode(e.target.value)}
            onKeyDown={handleKeyDown}
            spellCheck={false}
            placeholder="Paste your Python code here…"
          />
          <div className="cta">
            <button
              className="btn primary"
              onClick={generate}
              disabled={!canGenerate}
              title="Generate unit tests from the code above"
            >
              {loading ? "Generating…" : "Generate Tests"}
            </button>
          </div>
          <p className="hint">
            The backend injects this function into the generated tests so they run
            without separate imports. (Shortcut: Cmd/Ctrl + Enter)
          </p>
        </section>

        {/* Right: generated tests */}
        <section className="panel">
          <div className="panel-head">
            <h2>Generated Tests</h2>
            <div className="tools">
              <button className="btn ghost" onClick={() => copy(testCode)} disabled={!testCode.trim()}>
                Copy
              </button>
              <button
                className="btn ghost"
                onClick={() => download("test_generated.py", testCode)} disabled={!testCode.trim()}
              >
                Download.py
              </button>
            </div>
          </div>

          <textarea
            className={`editor ${loading ? "skeleton" : ""}`}
            value={loading ? "Generating tests…" : testCode}
            onChange={(e) => setTestCode(e.target.value)}
            spellCheck={false}
            placeholder="Your generated pytest code will appear here. You can edit it before downloading."
          />
          <p className="hint">Editable. Run with <code>pytest -q</code> in your project.</p>
        </section>
      </main>

      <footer className="footer">
        Backend: <code>{BACKEND_URL}</code> • Built with React + Vite
      </footer>
    </div>
  );
}