// AI designer settings: provider, model, base URL and effort (persisted as plain JSON in the Electron userData
// folder) and the request payload for /ws/ai. API keys are NOT part of these settings: they live encrypted in the
// main process (safeStorage) under secretName(provider).

export type ProviderId = "anthropic" | "openai" | "ollama";
export type Effort = "low" | "medium" | "high" | "xhigh" | "max";

export const EFFORTS: Effort[] = ["low", "medium", "high", "xhigh", "max"];
export const SETTINGS_KEY = "ai";

/** Entry of GET /api/ai/providers. */
export interface AiProvider {
  id: ProviderId;
  name: string;
  default_model: string;
  models?: string[];
  needs_key: boolean;
  base_url_hint?: string;
}

export interface AiSettings {
  provider: ProviderId;
  /** model per provider (empty = the provider's default) */
  models: Partial<Record<ProviderId, string>>;
  /** base URL per provider (openai / ollama) */
  baseUrls: Partial<Record<ProviderId, string>>;
  effort: Effort;
}

export const DEFAULT_SETTINGS: AiSettings = { provider: "anthropic", models: {}, baseUrls: {}, effort: "medium" };

const PROVIDER_IDS: ProviderId[] = ["anthropic", "openai", "ollama"];
const isProvider = (v: unknown): v is ProviderId => typeof v === "string" && (PROVIDER_IDS as string[]).includes(v);

function cleanMap(v: unknown): Partial<Record<ProviderId, string>> {
  const out: Partial<Record<ProviderId, string>> = {};
  if (!v || typeof v !== "object") return out;
  for (const [k, x] of Object.entries(v as Record<string, unknown>))
    if (isProvider(k) && typeof x === "string" && x.trim() && x.length <= 500) out[k] = x.trim();
  return out;
}

/** Accepts whatever was stored (possibly from an older version or hand-edited) and returns valid settings. */
export function normalizeSettings(raw: unknown): AiSettings {
  const r = raw && typeof raw === "object" ? (raw as Record<string, unknown>) : {};
  return {
    provider: isProvider(r.provider) ? r.provider : DEFAULT_SETTINGS.provider,
    models: cleanMap(r.models),
    baseUrls: cleanMap(r.baseUrls),
    effort: typeof r.effort === "string" && (EFFORTS as string[]).includes(r.effort) ? (r.effort as Effort) : DEFAULT_SETTINGS.effort,
  };
}

/** Name under which the provider's API key is kept in the encrypted secret store. */
export const secretName = (p: ProviderId) => `ai.apiKey.${p}`;

export const usesBaseUrl = (p: ProviderId) => p === "openai" || p === "ollama";
export const usesEffort = (p: ProviderId) => p === "anthropic";

/** Prefill for the base-URL box: the first URL found in the provider's hint ("https://... (or ...)"). */
export function baseUrlFromHint(hint: string | undefined): string {
  return hint?.match(/https?:\/\/\S+/)?.[0] ?? "";
}

export function modelFor(s: AiSettings, p: AiProvider | undefined): string {
  if (!p) return "";
  return s.models[p.id] || p.default_model;
}

export function baseUrlFor(s: AiSettings, p: AiProvider | undefined): string {
  if (!p || !usesBaseUrl(p.id)) return "";
  return s.baseUrls[p.id] ?? baseUrlFromHint(p.base_url_hint);
}

export function withModel(s: AiSettings, p: ProviderId, model: string): AiSettings {
  return { ...s, models: { ...s.models, [p]: model.trim() } };
}

export function withBaseUrl(s: AiSettings, p: ProviderId, url: string): AiSettings {
  return { ...s, baseUrls: { ...s.baseUrls, [p]: url.trim() } };
}

/** What is still missing before a chat can be sent (null = ready). */
export function missingSetting(s: AiSettings, p: AiProvider | undefined, apiKey: string | null): "provider" | "key" | "model" | null {
  if (!p) return "provider";
  if (p.needs_key && !apiKey) return "key";
  if (!modelFor(s, p)) return "model";
  return null;
}

export interface ChatRequest {
  type: "chat";
  session: string;
  text: string;
  provider: ProviderId;
  api_key: string | null;
  model: string;
  base_url: string | null;
  effort: Effort;
}

export function chatRequest(s: AiSettings, p: AiProvider, apiKey: string | null, session: string, text: string): ChatRequest {
  return {
    type: "chat",
    session,
    text,
    provider: p.id,
    api_key: p.needs_key ? apiKey : null,
    model: modelFor(s, p),
    base_url: baseUrlFor(s, p) || null,
    effort: s.effort,
  };
}
