import { describe, expect, it } from "vitest";
import {
  AiProvider, baseUrlFor, baseUrlFromHint, chatRequest, DEFAULT_SETTINGS, missingSetting, modelFor, normalizeSettings,
  secretName, withBaseUrl, withModel,
} from "./aiSettings";

const P: AiProvider[] = [
  { id: "anthropic", name: "Claude", default_model: "claude-opus-5-5", needs_key: true, models: ["claude-opus-5-5", "claude-haiku-5-5"] },
  { id: "openai", name: "OpenAI", default_model: "gpt-4.1", needs_key: true, base_url_hint: "https://api.openai.com/v1 (or OpenRouter...)" },
  { id: "ollama", name: "Ollama", default_model: "qwen2.5:14b", needs_key: false, base_url_hint: "http://localhost:11434/v1" },
];

describe("normalizeSettings", () => {
  it("returns defaults for garbage", () => {
    expect(normalizeSettings(null)).toEqual(DEFAULT_SETTINGS);
    expect(normalizeSettings("x")).toEqual(DEFAULT_SETTINGS);
    expect(normalizeSettings({ provider: "evil", effort: "turbo", models: 5 })).toEqual(DEFAULT_SETTINGS);
  });
  it("keeps valid fields and drops unknown providers, non-strings and stray keys", () => {
    const s = normalizeSettings({
      provider: "ollama", effort: "xhigh", models: { ollama: " llama3 ", foo: "x", openai: 3 },
      baseUrls: { openai: "http://h/v1" }, apiKey: "sk-should-not-survive",
    });
    expect(s).toEqual({ provider: "ollama", effort: "xhigh", models: { ollama: "llama3" }, baseUrls: { openai: "http://h/v1" } });
    expect(JSON.stringify(s)).not.toContain("sk-");
  });
  it("round-trips through JSON", () => {
    const s = withBaseUrl(withModel(DEFAULT_SETTINGS, "anthropic", "claude-haiku-5-5"), "openai", "https://openrouter.ai/api/v1");
    expect(normalizeSettings(JSON.parse(JSON.stringify(s)))).toEqual(s);
  });
});

describe("model / base URL resolution", () => {
  it("falls back to the provider default model", () => {
    expect(modelFor(DEFAULT_SETTINGS, P[0])).toBe("claude-opus-5-5");
    expect(modelFor(withModel(DEFAULT_SETTINGS, "anthropic", "claude-haiku-5-5"), P[0])).toBe("claude-haiku-5-5");
  });
  it("prefills the base URL from the hint, only for openai/ollama", () => {
    expect(baseUrlFromHint(P[1].base_url_hint)).toBe("https://api.openai.com/v1");
    expect(baseUrlFor(DEFAULT_SETTINGS, P[2])).toBe("http://localhost:11434/v1");
    expect(baseUrlFor(DEFAULT_SETTINGS, P[0])).toBe("");
  });
  it("secret names are per provider", () => {
    expect(secretName("openai")).toBe("ai.apiKey.openai");
  });
});

describe("chatRequest / missingSetting", () => {
  it("asks for a key only when the provider needs one", () => {
    expect(missingSetting(DEFAULT_SETTINGS, P[0], null)).toBe("key");
    expect(missingSetting(DEFAULT_SETTINGS, P[0], "k")).toBeNull();
    expect(missingSetting(DEFAULT_SETTINGS, P[2], null)).toBeNull();
    expect(missingSetting(DEFAULT_SETTINGS, undefined, "k")).toBe("provider");
  });
  it("builds the /ws/ai payload", () => {
    const r = chatRequest({ ...DEFAULT_SETTINGS, effort: "high" }, P[0], "sk", "s1", "hello");
    expect(r).toEqual({ type: "chat", session: "s1", text: "hello", provider: "anthropic", api_key: "sk", model: "claude-opus-5-5", base_url: null, effort: "high" });
    const o = chatRequest(DEFAULT_SETTINGS, P[2], "leaked?", "s1", "x");
    expect(o.api_key).toBeNull();
    expect(o.base_url).toBe("http://localhost:11434/v1");
  });
});
