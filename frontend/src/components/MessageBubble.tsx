import type { ChatResponse, QuestionType } from "../api";
import CitationsPanel from "./CitationsPanel";
import ConfidenceBadge from "./ConfidenceBadge";

const TYPE_LABELS: Record<QuestionType, string> = {
  single_fact: "Question factuelle",
  comparative: "Question comparative",
  out_of_scope: "Hors périmètre",
};

export default function MessageBubble({ turn }: { turn: ChatResponse }) {
  return (
    <div className="turn">
      <div className="turn__question">{turn.question}</div>
      <div className={`turn__answer ${turn.refused ? "turn__answer--refused" : ""}`}>
        <p>{turn.answer}</p>
        <div className="turn__meta">
          <ConfidenceBadge confidence={turn.confidence} refused={turn.refused} />
          <span className="type-tag">{TYPE_LABELS[turn.question_type]}</span>
        </div>
        <CitationsPanel citations={turn.citations} />
      </div>
    </div>
  );
}
