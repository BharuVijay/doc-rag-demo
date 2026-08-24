export type QuestionType = "single_fact" | "comparative" | "out_of_scope";
export type Confidence = "high" | "medium" | "low";

export interface Citation {
  doc_id: string;
  doc_title: string;
  section: string;
  page: number;
  snippet: string;
}

export interface EvidenceSpan {
  doc_id: string;
  page: number;
  quote: string;
}

export interface ChatResponse {
  question: string;
  question_type: QuestionType;
  answer: string;
  confidence: Confidence;
  refused: boolean;
  citations: Citation[];
  answer_found: boolean;
  complete_answer_found: boolean;
  evidence_spans: EvidenceSpan[];
  quotes: string[];
  latency_ms: number | null;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  retrieval_rank: number | null;
}

export interface DocumentSummary {
  doc_id: string;
  doc_title: string;
  pages: number;
}

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText}: ${body}`);
  }
  return res.json() as Promise<T>;
}

export function askQuestion(question: string): Promise<ChatResponse> {
  return fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  }).then((res) => asJson<ChatResponse>(res));
}

export function fetchDocuments(): Promise<DocumentSummary[]> {
  return fetch("/api/documents").then((res) => asJson<DocumentSummary[]>(res));
}
