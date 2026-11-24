"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, Asset } from "@/lib/api";

const disciplines = ["All disciplines", "Mechanical", "Electrical", "Controls", "Robotics", "Automation"];

export default function ReviewQueuePage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [discipline, setDiscipline] = useState("All disciplines");
  const [error, setError] = useState("");

  useEffect(() => {
    const query = discipline === "All disciplines" ? "" : `?discipline=${encodeURIComponent(discipline)}`;
    api<Asset[]>(`/api/review/queue${query}`).then(setAssets).catch((reason) => setError(reason.message));
  }, [discipline]);

  return (
    <>
      <div className="page-head">
        <div><div className="eyebrow">Mandatory engineering gate</div><h1>Engineering review</h1><div className="subtle">AI-derived assets remain drafts until qualified engineers validate them.</div></div>
        <label style={{ minWidth: 180 }}>Discipline
          <select value={discipline} onChange={(event) => setDiscipline(event.target.value)}>{disciplines.map((item) => <option key={item}>{item}</option>)}</select>
        </label>
      </div>
      {error && <div className="notice error">{error}</div>}
      <section className="card">
        <div className="section-head"><h2>Pending review <span className="muted">({assets.length})</span></h2></div>
        <div className="table-wrap">
          <table><thead><tr><th>Asset / ID</th><th>Source</th><th>Confidence</th><th>Risk</th><th>Discipline</th><th>Submission date</th><th /></tr></thead>
            <tbody>{assets.map((asset) => <tr key={asset.id}>
              <td><strong>{asset.title}</strong><div className="muted small">{asset.id}</div></td>
              <td>{asset.source_type}</td><td>{asset.confidence == null ? "Not scored" : `${Math.round(asset.confidence * 100)}%`}</td>
              <td>{asset.high_risk ? "Four-eye" : "Standard"}</td><td>{asset.discipline}</td>
              <td>{new Date(asset.created_at).toLocaleDateString()}</td><td><Link className="button secondary" href={`/assets/${asset.id}`}>Review</Link></td>
            </tr>)}</tbody>
          </table>
          {!assets.length && !error && <div className="empty">The review queue is clear.</div>}
        </div>
      </section>
    </>
  );
}
