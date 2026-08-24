import type { DocumentSummary } from "../api";

export default function DocumentSidebar({ documents }: { documents: DocumentSummary[] }) {
  return (
    <aside className="sidebar">
      <h2>Documents disponibles</h2>
      <p className="sidebar__hint">
        Corpus fictif à usage de démonstration — aucune donnée réelle de client.
      </p>
      <ul>
        {documents.map((doc) => (
          <li key={doc.doc_id}>{doc.doc_title}</li>
        ))}
      </ul>
    </aside>
  );
}
