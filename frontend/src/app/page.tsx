"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { API_URL, api, Asset } from "@/lib/api";

export default function HomePage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [discipline, setDiscipline] = useState("Mechanical");
  const [highRisk, setHighRisk] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function refresh() {
    try {
      setAssets(await api<Asset[]>("/api/assets"));
      setError("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Unable to load platform assets.");
    }
  }

  useEffect(() => { void refresh(); }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setMessage("");
    setError("");
    try {
      let created: Asset;
      if (file) {
        const formData = new FormData();
        formData.append("file", file);
        const query = new URLSearchParams({ discipline, high_risk: String(highRisk) });
        const response = await fetch(`${API_URL}/api/assets/upload?${query}`, { method: "POST", body: formData });
        if (!response.ok) {
          const body = await response.json().catch(() => null);
          throw new Error(body?.detail ?? `Upload failed (${response.status})`);
        }
        created = await response.json() as Asset;
      } else {
        created = await api<Asset>("/api/assets", {
          method: "POST",
          body: JSON.stringify({ title, source_url: url, discipline, high_risk: highRisk }),
        });
      }
      setTitle("");
      setUrl("");
      setFile(null);
      setMessage(`Asset created. Analysis job ${created.jobs[0]?.id ?? ""} is queued; AI output remains unapproved until engineering review.`);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Video intake failed.");
    } finally {
      setLoading(false);
    }
  }

  const pending = assets.filter((asset) => asset.status === "Pending Review").length;
  const released = assets.filter((asset) => asset.status === "Released").length;

  return (
    <>
      <div className="page-head">
        <div><div className="eyebrow">Industrial reverse engineering</div><h1>Engineering workspace</h1><div className="subtle">Transform machine media into validated, reusable engineering assets.</div></div>
        <Link className="button secondary" href="/engineering-review">Open review queue →</Link>
      </div>
      <div className="grid stats">
        <div className="card"><div className="stat-label">Total assets</div><div className="stat-value">{assets.length}</div></div>
        <div className="card"><div className="stat-label">Awaiting engineering review</div><div className="stat-value">{pending}</div></div>
        <div className="card"><div className="stat-label">Released digital twins</div><div className="stat-value">{released}</div></div>
      </div>
      <div className="detail-grid">
        <section className="card">
          <div className="section-head"><h2>Recent assets</h2><Link className="muted small" href="/library">Production library →</Link></div>
          {error && <div className="notice error">{error} Make sure the API is running.</div>}
          <div className="table-wrap">
            <table><thead><tr><th>Asset</th><th>Status</th><th>Confidence</th><th>Discipline</th></tr></thead>
              <tbody>{assets.slice(0, 8).map((asset) => <tr key={asset.id}>
                <td><Link href={`/assets/${asset.id}`}>{asset.title}</Link></td>
                <td><span className={`status ${asset.status === "Pending Review" ? "pending" : asset.status === "Released" ? "released" : ""}`}>{asset.status}</span></td>
                <td>{asset.confidence == null ? "—" : `${Math.round(asset.confidence * 100)}%`}</td><td>{asset.discipline}</td>
              </tr>)}</tbody>
            </table>
            {!assets.length && !error && <div className="empty">No assets yet. Add a machine video to start an engineering workflow.</div>}
          </div>
        </section>
        <section className="card">
          <div className="section-head"><h2>Ingest a machine video</h2></div>
          <p className="subtle">Create a library record and analysis job from a YouTube, Vimeo, or direct video URL.</p>
          {message && <div className="notice">{message}</div>}
          <form className="form-grid" onSubmit={submit}>
            <label>Asset title<input required={!file} maxLength={240} value={title} onChange={(event) => setTitle(event.target.value)} placeholder="e.g. Conveyor transfer station" /></label>
            <label>Video URL<input disabled={!!file} required={!file} type="url" value={url} onChange={(event) => setUrl(event.target.value)} placeholder="https://..." /></label>
            <label>Or upload a video file<input type="file" accept=".mp4,.mov,.webm,.m4v,video/mp4,video/quicktime,video/webm" onChange={(event) => setFile(event.target.files?.[0] ?? null)} /></label>
            <label>Engineering discipline<select value={discipline} onChange={(event) => setDiscipline(event.target.value)}><option>Mechanical</option><option>Electrical</option><option>Controls</option><option>Automation</option><option>Robotics</option></select></label>
            <label style={{ display: "flex", alignItems: "center", gap: 9 }}>
              <input type="checkbox" checked={highRisk} onChange={(event) => setHighRisk(event.target.checked)} style={{ width: "auto" }} />
              Mark as high-risk (requires independent Mechanical + Controls approval)
            </label>
            <div className="notice">Analysis workers and model providers are deployment integrations. The platform never marks AI output as approved automatically.</div>
            <button className="button" disabled={loading}>{loading ? "Creating asset…" : "Create analysis job"}</button>
          </form>
        </section>
      </div>
    </>
  );
}
