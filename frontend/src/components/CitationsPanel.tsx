import { useState } from "react";
import type { Citation } from "../api";

export default function CitationsPanel({ citations }: { citations: Citation[] }) {
  const [open, setOpen] = useState(false);

  if (citations.length === 0) return null;

  return (
    <div className="citations">
      <button className="citations__toggle" onClick={() => setOpen((v) => !v)}>
        {open ? "▾" : "▸"} {citations.length} source{citations.length > 1 ? "s" : ""}
      </button>
      {open && (
        <ul className="citations__list">
          {citations.map((c, i) => (
            <li key={i} className="citations__item">
              <div className="citations__item-header">
                <strong>{c.doc_title}</strong>
                <span className="citations__meta">
                  {c.section} · p.{c.page}
                </span>
              </div>
              <p className="citations__snippet">{c.snippet}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
