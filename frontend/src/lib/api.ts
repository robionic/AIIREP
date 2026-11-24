export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type Component = {
  id: string;
  name: string;
  component_type: string;
  confidence: number;
  description: string | null;
  approved: boolean;
  relationships: string[];
};

export type Asset = {
  id: string;
  title: string;
  source_url: string | null;
  source_type: string;
  status: string;
  confidence: number | null;
  discipline: string;
  high_risk: boolean;
  description: string | null;
  mechanism_graph: { nodes?: Array<{ id: string; label: string }>; edges?: Array<{ source: string; target: string; label?: string }> } | null;
  revision: number;
  created_at: string;
  components: Component[];
  jobs: Array<{ id: string; status: string; stage: string }>;
};

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
    cache: "no-store",
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new Error(body?.detail ?? `Request failed (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
