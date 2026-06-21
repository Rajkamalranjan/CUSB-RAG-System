"use client";

import { useMemo, useRef, useState } from "react";

const CUSB_LOGO = "https://cusb.ac.in/images/cusb/logo-new1.png";

type Source = {
  title?: string;
  source_file?: string;
  page?: number;
  url?: string;
  score?: number;
  citation_verified?: boolean;
};

type ChatTurn = {
  id: number;
  query: string;
  answer: string;
  sources: Source[];
};

export default function Home() {
  const [query, setQuery] = useState("");
  const [department, setDepartment] = useState("");
  const [category, setCategory] = useState("");
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [loading, setLoading] = useState(false);
  const [streaming, setStreaming] = useState(false);
  const [adminPassword, setAdminPassword] = useState("");
  const [token, setToken] = useState("");
  const [analytics, setAnalytics] = useState("");
  const [adminSummary, setAdminSummary] = useState("");
  const [adminStatus, setAdminStatus] = useState("");
  const fileRef = useRef<HTMLInputElement | null>(null);

  const latestAnswer = turns[0]?.answer || "";
  const examples = useMemo(
    () => [
      "give me full information about CUSB",
      "give me full information about Dr. Richa Vatsa",
      "faculty name statistics department",
      "hostel fee kya hai",
    ],
    []
  );

  function filters() {
    const values: Record<string, string> = {};
    if (department.trim()) values.department = department.trim();
    if (category.trim()) values.category = category.trim();
    return values;
  }

  function browserApiBase() {
    return process.env.NEXT_PUBLIC_BROWSER_API_BASE || "";
  }

  async function readJsonResponse(res: Response) {
    const text = await res.text();
    try {
      return text ? JSON.parse(text) : {};
    } catch {
      throw new Error(
        res.ok
          ? "Server returned an invalid response. Please try again."
          : `Server error (${res.status}). Please try again.`
      );
    }
  }

  async function ask(event?: { preventDefault: () => void }) {
    event?.preventDefault();
    const question = query.trim();
    if (!question || loading) return;

    setLoading(true);
    const turnId = Date.now();
    setTurns((items) => [{ id: turnId, query: question, answer: "", sources: [] }, ...items].slice(0, 20));
    setQuery("");
    const body = JSON.stringify({ query: question, filters: filters() });

    try {
      if (streaming) {
        await askStreaming(body, turnId);
        return;
      }

      const res = await fetch(`${browserApiBase()}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body,
      });
      const data = await readJsonResponse(res);
      if (!res.ok) {
        throw new Error(data.detail || data.error || "Request failed");
      }
      updateTurn(turnId, data.answer || "", data.sources || []);
    } catch (error) {
      updateTurn(turnId, error instanceof Error ? error.message : "Request failed", []);
    } finally {
      setLoading(false);
    }
  }

  function updateTurn(id: number, answer: string, sources: Source[]) {
    setTurns((items) => items.map((item) => (item.id === id ? { ...item, answer, sources } : item)));
  }

  async function askStreaming(body: string, turnId: number) {
    const apiBase = process.env.NEXT_PUBLIC_WS_BASE || browserApiBase();
    const wsBase = apiBase
      ? apiBase.replace(/^http/, "ws")
      : `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`;
    const wsUrl = wsBase + "/api/ws/chat";
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => ws.send(body);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "token") {
        setTurns((items) =>
          items.map((item) => (item.id === turnId ? { ...item, answer: item.answer + data.text } : item))
        );
      }
      if (data.type === "sources") {
        setTurns((items) =>
          items.map((item) => (item.id === turnId ? { ...item, sources: data.sources || [] } : item))
        );
      }
      if (data.type === "done") ws.close();
      if (data.type === "error") {
        updateTurn(turnId, data.error || "Streaming request failed", []);
        ws.close();
      }
    };

    await new Promise<void>((resolve) => {
      ws.onclose = () => resolve();
      ws.onerror = () => {
        updateTurn(turnId, "Streaming connection failed. Turn Streaming off and try again.", []);
        resolve();
      };
    });
  }

  async function login() {
    const res = await fetch(`${browserApiBase()}/api/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: "admin", password: adminPassword }),
    });
    const data = await res.json();
    setToken(data.access_token || "");
    setAdminStatus(data.ok ? "Admin logged in" : "Login failed");
    if (data.access_token) {
      await loadAdminStatus(data.access_token);
    }
  }

  async function loadAdminStatus(authToken = token) {
    if (!authToken) {
      setAdminStatus("Login first");
      return;
    }
    const res = await fetch(`${browserApiBase()}/api/admin/status`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    setAdminSummary(JSON.stringify(await res.json(), null, 2));
  }

  async function loadHealth() {
    const res = await fetch(`${browserApiBase()}/api/health`);
    setAdminSummary(JSON.stringify(await res.json(), null, 2));
  }

  async function adminAction(path: string, method = "POST") {
    if (!token) {
      setAdminStatus("Login first");
      return;
    }
    const res = await fetch(`${browserApiBase()}/api/${path}`, {
      method,
      headers: { Authorization: `Bearer ${token}` },
    });
    setAdminStatus(JSON.stringify(await res.json(), null, 2));
  }

  async function loadAnalytics() {
    if (!token) {
      setAdminStatus("Login first");
      return;
    }
    const res = await fetch(`${browserApiBase()}/api/analytics`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    setAnalytics(JSON.stringify(await res.json(), null, 2));
  }

  async function sendFeedback(turn: ChatTurn, rating: "good" | "weak") {
    await fetch(`${browserApiBase()}/api/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ rating, query: turn.query, answer: turn.answer }),
    });
    setAdminStatus(rating === "good" ? "Feedback recorded: good answer" : "Feedback recorded: weak answer");
  }

  async function copyAnswer(answer: string) {
    if (!answer) return;
    await navigator.clipboard?.writeText(answer);
  }

  async function uploadPdf(file?: File) {
    if (!file || !token) {
      setAdminStatus("Choose a PDF and login first");
      return;
    }
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${browserApiBase()}/api/upload`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    });
    setAdminStatus(JSON.stringify(await res.json(), null, 2));
  }

  return (
    <main className="min-h-screen bg-[#f7f7f4] text-[#1f1f1d]">
      <div className="grid min-h-screen lg:grid-cols-[300px_1fr]">
        <aside className="hidden border-r border-[#ded8cf] bg-[#fbfaf8] p-4 lg:flex lg:flex-col">
          <div className="flex items-center gap-3 border-b border-[#e6dfd7] pb-4">
            <img className="h-14 w-14 shrink-0 rounded-full object-contain" src={CUSB_LOGO} alt="" />
            <div>
              <h1 className="text-base font-semibold">CUSB RAG</h1>
              <p className="text-xs text-[#6d6258]">Citation-grounded assistant</p>
            </div>
          </div>

          <button
            className="mt-4 rounded-md border border-[#d8cec2] bg-white px-3 py-2 text-left text-sm font-medium shadow-sm"
            onClick={() => {
              setQuery("");
              setTurns([]);
            }}
          >
            New chat
          </button>
          <button
            className="mt-2 rounded-md border border-[#d8cec2] bg-white px-3 py-2 text-left text-sm font-medium shadow-sm"
            onClick={() => setTurns([])}
          >
            Clear history
          </button>

          <section className="mt-5 min-h-0 flex-1 overflow-auto">
            <h2 className="mb-2 px-1 text-xs font-semibold uppercase tracking-wide text-[#81766b]">History</h2>
            <div className="space-y-1">
              {turns.map((turn) => (
                <button
                  key={turn.id}
                  className="line-clamp-2 w-full rounded-md px-3 py-2 text-left text-sm text-[#39342f] hover:bg-[#eee8e1]"
                  onClick={() => setQuery(turn.query)}
                >
                  {turn.query}
                </button>
              ))}
            </div>
          </section>

          <section className="mt-4 space-y-2 border-t border-[#e6dfd7] pt-4">
            <h2 className="text-xs font-semibold uppercase tracking-wide text-[#81766b]">Admin</h2>
            <input
              className="w-full rounded-md border border-[#d8cec2] bg-white px-3 py-2 text-sm outline-none"
              type="password"
              value={adminPassword}
              onChange={(e) => setAdminPassword(e.target.value)}
              placeholder="Admin password"
            />
            <button className="w-full rounded-md bg-[#8f1d10] px-3 py-2 text-sm font-medium text-white" onClick={login}>
              Login
            </button>
            <input ref={fileRef} className="hidden" type="file" accept="application/pdf" onChange={(e) => uploadPdf(e.target.files?.[0])} />
            <div className="grid grid-cols-2 gap-2">
              <button className="rounded-md border border-[#d8cec2] bg-white px-2 py-2 text-xs" onClick={() => fileRef.current?.click()}>
                Upload
              </button>
              <button className="rounded-md border border-[#d8cec2] bg-white px-2 py-2 text-xs" onClick={() => adminAction("documents", "GET")}>
                Docs
              </button>
              <button className="rounded-md border border-[#d8cec2] bg-white px-2 py-2 text-xs" onClick={() => adminAction("reindex")}>
                Reindex
              </button>
              <button className="rounded-md border border-[#d8cec2] bg-white px-2 py-2 text-xs" onClick={loadAnalytics}>
                Analytics
              </button>
              <button className="rounded-md border border-[#d8cec2] bg-white px-2 py-2 text-xs" onClick={loadHealth}>
                Health
              </button>
              <button className="rounded-md border border-[#d8cec2] bg-white px-2 py-2 text-xs" onClick={() => loadAdminStatus()}>
                Status
              </button>
            </div>
            <pre className="max-h-24 overflow-auto rounded-md bg-[#f0ebe4] p-2 text-xs text-[#5f554b]">
              {adminStatus || adminSummary || analytics || "Admin status"}
            </pre>
          </section>
        </aside>

        <section className="flex min-h-screen flex-col">
          <header className="sticky top-0 z-10 border-b border-[#e2dbd2] bg-[#f7f7f4]/95 px-4 py-3 backdrop-blur">
            <div className="mx-auto flex max-w-4xl items-center justify-between gap-3">
              <div className="flex items-center gap-3">
                <img className="h-10 w-10 rounded-full object-contain lg:hidden" src={CUSB_LOGO} alt="" />
                <div>
                  <h1 className="text-sm font-semibold sm:text-base">Central University of South Bihar Assistant</h1>
                  <p className="text-xs text-[#766b61]">Ask about admissions, courses, faculty, hostel, syllabus, and campus info.</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button
                  className="rounded-md border border-[#d8cec2] bg-white px-3 py-2 text-xs font-medium text-[#5b5148] lg:hidden"
                  onClick={() => {
                    setQuery("");
                    setTurns([]);
                  }}
                >
                  New
                </button>
                <label className="flex items-center gap-2 rounded-md border border-[#d8cec2] bg-white px-3 py-2 text-xs text-[#5b5148]">
                  <input type="checkbox" checked={streaming} onChange={(e) => setStreaming(e.target.checked)} />
                  Streaming
                </label>
              </div>
            </div>
          </header>

          <details className="border-b border-[#e2dbd2] bg-[#fbfaf8] px-4 py-3 lg:hidden">
            <summary className="cursor-pointer text-sm font-medium text-[#5a4f45]">Admin and filters</summary>
            <div className="mt-3 grid gap-2">
              <div className="grid gap-2 sm:grid-cols-2">
                <input
                  className="rounded-md border border-[#d8cec2] bg-white px-3 py-2 text-sm outline-none"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  placeholder="Department filter"
                />
                <input
                  className="rounded-md border border-[#d8cec2] bg-white px-3 py-2 text-sm outline-none"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  placeholder="Category filter"
                />
              </div>
              <div className="grid gap-2 sm:grid-cols-[1fr_auto_auto]">
                <input
                  className="rounded-md border border-[#d8cec2] bg-white px-3 py-2 text-sm outline-none"
                  type="password"
                  value={adminPassword}
                  onChange={(e) => setAdminPassword(e.target.value)}
                  placeholder="Admin password"
                />
                <button className="rounded-md bg-[#8f1d10] px-3 py-2 text-sm font-medium text-white" onClick={login}>
                  Login
                </button>
                <button className="rounded-md border border-[#d8cec2] bg-white px-3 py-2 text-sm" onClick={loadHealth}>
                  Health
                </button>
              </div>
            </div>
          </details>

          <div className="flex-1 overflow-auto px-4 py-6">
            <div className="mx-auto max-w-4xl space-y-7">
              {turns.length === 0 ? (
                <section className="flex min-h-[54vh] flex-col items-center justify-center text-center">
                  <img className="h-24 w-24 rounded-full object-contain shadow-sm" src={CUSB_LOGO} alt="" />
                  <h2 className="mt-5 text-2xl font-semibold">How can I help you today?</h2>
                  <div className="mt-6 grid w-full max-w-3xl gap-3 sm:grid-cols-2">
                    {examples.map((example) => (
                      <button
                        key={example}
                        className="rounded-md border border-[#ded5ca] bg-white p-4 text-left text-sm shadow-sm hover:bg-[#fbf8f3]"
                        onClick={() => setQuery(example)}
                      >
                        {example}
                      </button>
                    ))}
                  </div>
                </section>
              ) : null}

              {[...turns].reverse().map((turn) => (
                <article key={turn.id} className="space-y-4">
                  <div className="flex justify-end">
                    <div className="max-w-[82%] rounded-md bg-[#8f1d10] px-4 py-3 text-sm leading-6 text-white shadow-sm">
                      {turn.query}
                    </div>
                  </div>
                  <div className="flex gap-3">
                    <img className="mt-1 h-8 w-8 shrink-0 rounded-full object-contain" src={CUSB_LOGO} alt="" />
                    <div className="min-w-0 flex-1">
                      <div className="whitespace-pre-wrap rounded-md border border-[#e1d9ce] bg-white px-4 py-3 text-sm leading-7 shadow-sm">
                        {turn.answer || (loading && turn.id === turns[0]?.id ? "Searching CUSB sources..." : latestAnswer ? "" : "Searching CUSB sources...")}
                      </div>
                      <div className="mt-2 flex flex-wrap gap-2">
                        <button
                          className="rounded-md border border-[#d8cec2] bg-white px-2 py-1 text-xs text-[#5b5148]"
                          onClick={() => copyAnswer(turn.answer)}
                          disabled={!turn.answer}
                        >
                          Copy
                        </button>
                        <button
                          className="rounded-md border border-[#d8cec2] bg-white px-2 py-1 text-xs text-[#5b5148]"
                          onClick={() => sendFeedback(turn, "good")}
                          disabled={!turn.answer}
                        >
                          Good
                        </button>
                        <button
                          className="rounded-md border border-[#d8cec2] bg-white px-2 py-1 text-xs text-[#5b5148]"
                          onClick={() => sendFeedback(turn, "weak")}
                          disabled={!turn.answer}
                        >
                          Weak
                        </button>
                      </div>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          </div>

          <footer className="border-t border-[#e2dbd2] bg-[#f7f7f4] px-4 py-4">
            <form onSubmit={ask} className="mx-auto max-w-4xl">
              <div className="mb-2 grid gap-2 sm:grid-cols-2">
                <input
                  className="rounded-md border border-[#d8cec2] bg-white px-3 py-2 text-sm outline-none focus:border-[#8f1d10]"
                  value={department}
                  onChange={(e) => setDepartment(e.target.value)}
                  placeholder="Department filter"
                />
                <input
                  className="rounded-md border border-[#d8cec2] bg-white px-3 py-2 text-sm outline-none focus:border-[#8f1d10]"
                  value={category}
                  onChange={(e) => setCategory(e.target.value)}
                  placeholder="Category filter"
                />
              </div>
              <div className="flex items-end gap-2 rounded-md border border-[#d8cec2] bg-white p-2 shadow-sm">
                <textarea
                  className="max-h-36 min-h-12 flex-1 resize-none bg-transparent px-2 py-2 text-sm outline-none"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) ask(e);
                  }}
                  placeholder="Message CUSB RAG..."
                />
                <button
                  className="h-10 rounded-md bg-[#8f1d10] px-4 text-sm font-semibold text-white disabled:opacity-60"
                  disabled={loading || !query.trim()}
                  type="submit"
                >
                  {loading ? "..." : "Ask"}
                </button>
              </div>
              <p className="mt-2 text-center text-xs text-[#81766b]">Answers are generated from indexed CUSB sources.</p>
            </form>
          </footer>
        </section>
      </div>
    </main>
  );
}
