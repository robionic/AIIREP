"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api, Asset } from "@/lib/api";

export default function LibraryPage() {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [error, setError] = useState("");
  useEffect(() => { api<Asset[]>("/api/library").then(setAssets).catch((reason) => setError(reason.message)); }, []);

  return (
    <>
      <div className="page-head"><div><div className="eyebrow">Validated knowledge assets</div><h1>Production library</h1><div className="subtle">Only released digital twins are published here.</div></div></div>
      {error && <div className="notice error">{error}</div>}
      <section className="card">
        <div className="table-wrap"><table><thead><tr><th>Asset</th><th>Discipline</th><th>Confidence</th><th>Revision</th><th>Released</th></tr></thead>
          <tbody>{assets.map((asset) => <tr key={asset.id}><td><Link href={`/assets/${asset.id}`}>{asset.title}</Link></td><td>{asset.discipline}</td><td>{asset.confidence == null ? "—" : `${Math.round(asset.confidence * 100)}%`}</td><td>R{asset.revision}</td><td><span className="status released">Released</span></td></tr>)}</tbody>
        </table>{!assets.length && !error && <div className="empty">No assets have passed engineering release yet.</div>}</div>
      </section>
    </>
  );
}
