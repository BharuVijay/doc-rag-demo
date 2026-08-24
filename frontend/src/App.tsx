import { useEffect, useRef, useState } from "react";
import { askQuestion, fetchDocuments, type ChatResponse, type DocumentSummary } from "./api";
import DocumentSidebar from "./components/DocumentSidebar";
import MessageBubble from "./components/MessageBubble";

const EXAMPLE_QUESTIONS = [
  "Quelle est la franchise pour un dégât des eaux ?",
  "Quelle est la différence de franchise vol entre l'auto et l'habitation ?",
  "Quel est le prix d'un billet d'avion pour Tokyo ?",
];

export default function App() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [turns, setTurns] = useState<ChatResponse[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchDocuments().then(setDocuments).catch(() => setDocuments([]));
  }, []);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [turns, loading]);

  async function submitQuestion(question: string) {
    const trimmed = question.trim();
    if (!trimmed || loading) return;
    setLoading(true);
    setError(null);
    try {
      const response = await askQuestion(trimmed);
      setTurns((prev) => [...prev, response]);
      setInput("");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erreur inconnue.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="app">
      <DocumentSidebar documents={documents} />
      <main className="chat">
        <header className="chat__header">
          <h1>Assistant Documentaire — Assurances Solidaris</h1>
          <p>Démo — données et compagnie fictives, aucune information réelle de client.</p>
        </header>

        <div className="chat__log">
          {turns.length === 0 && (
            <div className="chat__empty">
              <p>Posez une question sur les contrats auto, habitation, vie/santé ou un sinistre.</p>
              <div className="examples">
                {EXAMPLE_QUESTIONS.map((q) => (
                  <button key={q} className="examples__chip" onClick={() => submitQuestion(q)}>
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}
          {turns.map((turn, i) => (
            <MessageBubble key={i} turn={turn} />
          ))}
          {loading && <div className="turn__loading">Recherche dans les documents…</div>}
          {error && <div className="turn__error">{error}</div>}
          <div ref={bottomRef} />
        </div>

        <form
          className="chat__input"
          onSubmit={(e) => {
            e.preventDefault();
            submitQuestion(input);
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Votre question…"
            disabled={loading}
          />
          <button type="submit" disabled={loading || !input.trim()}>
            Envoyer
          </button>
        </form>
      </main>
    </div>
  );
}
