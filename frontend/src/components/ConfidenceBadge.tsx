import type { Confidence } from "../api";

const LABELS: Record<Confidence, string> = {
  high: "Confiance haute",
  medium: "Confiance moyenne",
  low: "Confiance faible",
};

export default function ConfidenceBadge({
  confidence,
  refused,
}: {
  confidence: Confidence;
  refused: boolean;
}) {
  const cls = refused ? "badge badge--refused" : `badge badge--${confidence}`;
  const label = refused ? "Réponse refusée" : LABELS[confidence];
  return <span className={cls}>{label}</span>;
}
