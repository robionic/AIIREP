"use client";

import dynamic from "next/dynamic";
import Link from "next/link";
import { useParams } from "next/navigation";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { API_URL, api, Asset } from "@/lib/api";

const MechanismEditor = dynamic(() => import("@/components/MechanismEditor"), { ssr: false });
const TwinViewer = dynamic(() => import("@/components/TwinViewer"), { ssr: false });

type AuditEntry = { id: string; actor: string; role: string; action: string; comment: string | null; revision: number; created_at: string };
const roles = ["Mechanical Engineer", "Controls Engineer", "Electrical Engineer", "Automation Engineer", "Robotics Engineer", "Senior Reviewer", "Administrator"];

export default function AssetDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [asset, setAsset] = useState<Asset | null>(null);
  const [audit, setAudit] = useState<AuditEntry[]>([]);
  const [actor, setActor] = useState("Review Engineer");
  const [role, setRole] = useState(roles[0]);
  const [comment, setComment] = useState("");
  const [kinematics, setKinematics] = useState('{"joints":[],"constraints":[]}');
  const [componentNames, setComponentNames] = useState<Record<string, string>>({});
  const [newComponent, setNewComponent] = useState("");
  const [newComponentType, setNewComponentType] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);

  const refresh = useCallback(async () => {
    const [current, events] = await Promise.all([
      api<Asset>(`/api/assets/${id}`),
      api<AuditEntry[]>(`/api/assets/${id}/audit`),
    ]);
    setAsset(current);
    setAudit(events);
    setComponentNames(Object.fromEntries(current.components.map((component) => [component.id, component.name])));
    if (current.kinematic_model) setKinematics(JSON.stringify(current.kinematic_model, null, 2));
  }, [id]);

  useEffect(() => { void refresh().catch((reason) => setError(reason.message)); }, [refresh]);

  async function perform(action: () => Promise<unknown>, success: string) {
    setSaving(true);
    setError("");
    setNotice("");
    try {
      await action();
      setNotice(success);
      await refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Action failed.");
    } finally {
      setSaving(false);
    }
  }

  function decide(action: string) {
    if (!comment.trim()) { setError("Enter a review comment before recording a decision."); return; }
    return perform(() => api(`/api/assets/${id}/decision`, {
      method: "POST",
      body: JSON.stringify({ actor, role, action, comment }),
    }), `Decision recorded: ${action.replaceAll("_", " ")}.`);
  }

  async function release() {
    if (!comment.trim()) { setError("Enter an approval comment before release."); return; }
    return perform(() => api(`/api/assets/${id}/release`, {
      method: "POST",
      body: JSON.stringify({ actor, role, comment }),
    }), "Asset released to the production library.");
  }

  if (!asset && error) return <div className="notice error">{error}<p><Link href="/">Return to workspace</Link></p></div>;
  if (!asset) return <div className="muted">Loading engineering asset…</div>;

  return (
    <>
      <div className="page-head">
        <div><div className="eyebrow"><Link href="/engineering-review">Engineering review</Link> / Asset</div><h1>{asset.title}</h1>
          <div className="subtle">{asset.id} · Revision {asset.revision} · {asset.discipline}</div></div>
        <span className={`status ${asset.status === "Pending Review" ? "pending" : asset.status === "Released" ? "released" : ""}`}>{asset.status}</span>
      </div>
      {error && <div className="notice error">{error}</div>}
      {notice && <div className="notice">{notice}</div>}
      <section className="card" style={{ marginBottom: 16 }}>
        <div className="section-head"><h2>Source video</h2><span className="muted small">{asset.source_type}</span></div>
        {asset.source_type === "upload"
          ? <video controls preload="metadata" style={{ width: "100%", maxHeight: 420, background: "#05090d", borderRadius: 8 }} src={`${API_URL}/api/assets/${asset.id}/media`} />
          : asset.source_url && <a className="button secondary" href={asset.source_url} target="_blank" rel="noreferrer">Open source video ↗</a>}
      </section>
      <div className="detail-grid">
        <div className="grid">
          <section className="card">
            <div className="section-head"><h2>Interactive digital twin preview</h2><span className="muted small">schematic geometry</span></div>
            <TwinViewer asset={asset} />
          </section>
          <section className="card">
            <div className="section-head"><h2>Mechanism graph</h2><span className="muted small">Revision {asset.revision}</span></div>
            <MechanismEditor asset={asset} onSaved={() => { void refresh(); }} />
          </section>
          <section className="card">
            <div className="section-head"><h2>Kinematic model</h2></div>
            <div className="notice">Joint definitions must be verified by an engineer. Edits create a new revision and invalidate prior signatures.</div>
            <form className="form-grid" onSubmit={(event: FormEvent) => {
              event.preventDefault();
              void perform(async () => {
                const model = JSON.parse(kinematics);
                await api(`/api/assets/${id}/kinematics?actor=${encodeURIComponent(actor)}`, { method: "PUT", body: JSON.stringify(model) });
              }, "Kinematic model saved as a new review revision.");
            }}>
              <label>Joint and constraint JSON<textarea rows={7} value={kinematics} onChange={(event) => setKinematics(event.target.value)} /></label>
              <button disabled={saving || asset.status === "Released"} className="button secondary">Save kinematics</button>
            </form>
          </section>
        </div>
        <div className="grid">
          <section className="card">
            <div className="section-head"><h2>Component validation</h2><span className="muted">{asset.components.length} items</span></div>
            {!asset.components.length && <div className="empty">No model detections are available. Add a missing component below or connect an analysis provider.</div>}
            {asset.components.map((component) => <div className="component" key={component.id}>
              <div style={{ flex: 1 }}>
                <input aria-label="Component name" value={componentNames[component.id] ?? component.name} disabled={asset.status === "Released"} onChange={(event) => setComponentNames((current) => ({ ...current, [component.id]: event.target.value }))} />
                <div className="muted small">{component.component_type} · <span className="confidence">{Math.round(component.confidence * 100)}%</span></div><div className="muted small">{component.description}</div>
              </div>
              <div className="toolbar">
                {componentNames[component.id] !== component.name && <button disabled={saving || asset.status === "Released"} className="button secondary" onClick={() => void perform(() => api(`/api/assets/${id}/components/${component.id}?actor=${encodeURIComponent(actor)}&role=${encodeURIComponent(role)}`, {
                  method: "PATCH", body: JSON.stringify({ name: componentNames[component.id] }),
                }), "Component correction recorded.")}>Save name</button>}
                <button disabled={saving || component.approved || asset.status === "Released"} className={`button ${component.approved ? "secondary" : ""}`} onClick={() => void perform(() => api(`/api/assets/${id}/components/${component.id}?actor=${encodeURIComponent(actor)}&role=${encodeURIComponent(role)}`, {
                  method: "PATCH", body: JSON.stringify({ approved: true }),
                }), "Detection approved; revision updated.")}>{component.approved ? "Validated" : "Approve"}</button>
                <button disabled={saving || asset.status === "Released"} className="button danger" onClick={() => void perform(() => api(`/api/assets/${id}/components/${component.id}?actor=${encodeURIComponent(actor)}&role=${encodeURIComponent(role)}`, { method: "DELETE" }), "Component removed and audited.")}>Remove</button>
              </div>
            </div>)}
            <form className="form-grid" style={{ marginTop: 16 }} onSubmit={(event) => {
              event.preventDefault();
              void perform(async () => {
                await api(`/api/assets/${id}/components?actor=${encodeURIComponent(actor)}&role=${encodeURIComponent(role)}`, {
                  method: "POST",
                  body: JSON.stringify({ name: newComponent, component_type: newComponentType, confidence: 0, description: "Engineer-added component; no AI confidence assigned." }),
                });
                setNewComponent("");
                setNewComponentType("");
              }, "Missing component added and audited.");
            }}>
              <div className="section-head"><h2>Add missing component</h2></div>
              <div className="toolbar">
                <input aria-label="New component name" required disabled={asset.status === "Released"} value={newComponent} onChange={(event) => setNewComponent(event.target.value)} placeholder="Component name" />
                <input aria-label="New component type" required disabled={asset.status === "Released"} value={newComponentType} onChange={(event) => setNewComponentType(event.target.value)} placeholder="Type" />
                <button className="button secondary" disabled={saving || asset.status === "Released"}>Add</button>
              </div>
            </form>
          </section>
          <section className="card">
            <div className="section-head"><h2>Engineering decision</h2></div>
            <div className="notice">Policy escalation: confidence under 80% requires Mechanical + Controls; 80–95% requires Mechanical; high-risk requires two independent approvals. All detected components must be validated before release.</div>
            <div className="form-grid">
              <label>Reviewer name<input value={actor} onChange={(event) => setActor(event.target.value)} /></label>
              <label>Engineering role<select value={role} onChange={(event) => setRole(event.target.value)}>{roles.map((item) => <option key={item}>{item}</option>)}</select></label>
              <label>Review / release comment<textarea rows={3} value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Record engineering rationale and limitations" /></label>
              {asset.status === "Draft" && <button className="button" disabled={saving} onClick={() => void perform(() => api(`/api/assets/${id}/submit`, { method: "POST" }), "Submitted to engineering review.")}>Submit for review</button>}
              {asset.status === "Pending Review" && <div className="toolbar">
                <button className="button" disabled={saving} onClick={() => void decide("approve")}>Approve</button>
                <button className="button secondary" disabled={saving} onClick={() => void decide("approve_with_changes")}>Approve with changes</button>
                <button className="button danger" disabled={saving} onClick={() => void decide("reject")}>Reject</button>
              </div>}
              {asset.status === "Approved With Changes" && <button className="button" disabled={saving} onClick={() => void perform(() => api(`/api/assets/${id}/signatures`, { method: "POST", body: JSON.stringify({ reviewer: actor, role, comment }) }), "Validation signature recorded.")}>Record validation signature</button>}
              {asset.status === "Approved" && <button className="button" disabled={saving} onClick={() => void release()}>Release to production library</button>}
              {asset.status === "Released" && <div className="notice">Released and visible in the production library. Changes require a new revision.</div>}
            </div>
          </section>
          <section className="card">
            <div className="section-head"><h2>Immutable audit trail</h2><span className="muted">{audit.length} events</span></div>
            {audit.map((entry) => <div className="audit-row" key={entry.id}>
              <strong>{entry.action.replaceAll("_", " ")}</strong>
              <div className="muted small">{entry.actor} · {entry.role} · R{entry.revision} · {new Date(entry.created_at).toLocaleString()}</div>
              {entry.comment && <div className="muted small">{entry.comment}</div>}
            </div>)}
          </section>
        </div>
      </div>
    </>
  );
}
