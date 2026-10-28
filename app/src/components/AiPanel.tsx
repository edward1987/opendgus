// AI designer tab: streamed chat with the backend agent (/ws/ai) and the provider settings.
import { Fragment, ReactNode, useEffect, useLayoutEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { currentProvider, useAi } from "../aiStore";
import { ChatItem, inputPreview } from "../lib/aiChat";
import { baseUrlFor, EFFORTS, missingSetting, modelFor, usesBaseUrl, usesEffort, withBaseUrl, withModel } from "../lib/aiSettings";
import { useStore } from "../store";
import { Icon } from "./Icons";

const SUGGESTIONS = ["s1", "s2", "s3", "s4", "s5"];

export function AiPanel() {
  const { t } = useTranslation();
  const ai = useAi();
  const smokeAiDemo = useStore((s) => s.smokeAiDemo);
  const prov = currentProvider(ai);
  const missing = ai.loaded ? missingSetting(ai.settings, prov, prov ? ai.keys[prov.id] ?? null : null) : null;

  useEffect(() => {
    if (smokeAiDemo !== null) {
      void ai.loadDemo(smokeAiDemo).then(() =>
        setTimeout(() => requestAnimationFrame(() => useStore.getState().markRendered(true)), 400));
    } else void ai.load();
  }, []);

  return (
    <div className="ai-chat">
      <div className="ai-head">
        <button className={`ai-prov ${ai.settingsOpen ? "on" : ""}`} onClick={() => ai.setSettingsOpen(!ai.settingsOpen)} title={t("ai.settings")}>
          <Icon name="gear" size={14} />
          <span className="ai-prov-name">{prov ? prov.name : t("ai.provider")}</span>
          {prov && <span className="ai-prov-model">{modelFor(ai.settings, prov)}</span>}
          <Icon name={ai.settingsOpen ? "up" : "down"} size={12} />
        </button>
        <button className="icon-btn" title={t("ai.mcpConnect")} onClick={() => useStore.getState().setDialog("mcp")}>
          <Icon name="plug" />
        </button>
        <button className="icon-btn" title={t("ai.reset")} disabled={!ai.chat.items.length} onClick={() => ai.reset()}>
          <Icon name="newChat" />
        </button>
      </div>
      {ai.settingsOpen && <AiSettingsForm />}
      {ai.providersError && <div className="alert error small">{t("ai.providersError", { error: ai.providersError })}</div>}
      <Transcript />
      <Composer missing={missing} />
    </div>
  );
}

// ------------------------------------------------------------------ settings

function AiSettingsForm() {
  const { t } = useTranslation();
  const ai = useAi();
  const prov = currentProvider(ai);
  const [keyDraft, setKeyDraft] = useState("");
  const [replacing, setReplacing] = useState(false);
  const [customModel, setCustomModel] = useState(false);
  if (!prov) return null;
  const s = ai.settings;
  const model = modelFor(s, prov);
  const listed = prov.models?.length ? prov.models : null;
  const showCustom = !listed || customModel || !listed.includes(model);
  const key = ai.keys[prov.id];

  const saveKey = async () => {
    await ai.setApiKey(prov.id, keyDraft);
    setKeyDraft("");
    setReplacing(false);
  };

  return (
    <div className="ai-settings">
      <label className="field">
        <span>{t("ai.provider")}</span>
        <select value={prov.id} onChange={(e) => { ai.updateSettings({ ...s, provider: e.target.value as typeof s.provider }); setReplacing(false); setCustomModel(false); }}>
          {ai.providers.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
      </label>
      <label className="field">
        <span>{t("ai.model")}</span>
        {listed && (
          <select value={showCustom ? "__other" : model} onChange={(e) => {
            if (e.target.value === "__other") setCustomModel(true);
            else { setCustomModel(false); ai.updateSettings(withModel(s, prov.id, e.target.value)); }
          }}>
            {listed.map((m) => <option key={m} value={m}>{m}</option>)}
            <option value="__other">{t("ai.modelOther")}</option>
          </select>
        )}
        {showCustom && (
          <input className="mono" placeholder={prov.default_model} defaultValue={listed && listed.includes(model) ? "" : s.models[prov.id] ?? ""}
            aria-label={t("ai.modelCustom")}
            onBlur={(e) => ai.updateSettings(withModel(s, prov.id, e.target.value))}
            onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }} />
        )}
      </label>
      {prov.needs_key && (
        <div className="field">
          <span>{t("ai.apiKey")}</span>
          {key && !replacing ? (
            <div className="ai-key-row">
              <Icon name="key" size={14} />
              <span className="mono">••••••••{key.length > 8 ? key.slice(-4) : ""}</span>
              <span className="grow muted small ellipsis" title={ai.keyPersisted[prov.id] ? t("ai.apiKeySaved") : t("ai.apiKeySession")}>{ai.keyPersisted[prov.id] ? t("ai.apiKeySaved") : t("ai.apiKeySession")}</span>
              <button className="btn sm ghost" onClick={() => setReplacing(true)}>{t("ai.apiKeyReplace")}</button>
              <button className="btn sm ghost" onClick={() => void ai.removeApiKey(prov.id)}>{t("ai.apiKeyRemove")}</button>
            </div>
          ) : (
            <div className="row gap">
              <input type="password" autoComplete="off" spellCheck={false} placeholder={t("ai.apiKeyPlaceholder")} value={keyDraft}
                onChange={(e) => setKeyDraft(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter") void saveKey(); }} />
              <button className="btn sm primary" disabled={!keyDraft.trim()} onClick={() => void saveKey()}>{t("ai.save")}</button>
            </div>
          )}
        </div>
      )}
      {usesBaseUrl(prov.id) && (
        <label className="field">
          <span>{t("ai.baseUrl")}</span>
          <input className="mono" key={prov.id} defaultValue={baseUrlFor(s, prov)} placeholder={prov.base_url_hint}
            onBlur={(e) => ai.updateSettings(withBaseUrl(s, prov.id, e.target.value))}
            onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); }} />
        </label>
      )}
      {usesEffort(prov.id) && (
        <div className="field">
          <span>{t("ai.effort")}</span>
          <div className="segmented">
            {EFFORTS.map((x) => (
              <button key={x} className={s.effort === x ? "on" : ""} onClick={() => ai.updateSettings({ ...s, effort: x })}>{t(`ai.effort_${x}`)}</button>
            ))}
          </div>
          <span className="muted small">{t("ai.effortHint")}</span>
        </div>
      )}
    </div>
  );
}

// ------------------------------------------------------------------ transcript

function Transcript() {
  const { t } = useTranslation();
  const chat = useAi((s) => s.chat);
  const send = useAi((s) => s.send);
  const ref = useRef<HTMLDivElement>(null);
  const stick = useRef(true);

  useLayoutEffect(() => {
    const el = ref.current;
    if (el && stick.current) el.scrollTop = el.scrollHeight;
  }, [chat]);

  const last = chat.items[chat.items.length - 1];
  const streaming = chat.running && last && (last.kind === "assistant" || last.kind === "thinking");

  return (
    <div className="ai-log" ref={ref} onScroll={(e) => {
      const el = e.currentTarget;
      stick.current = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
    }}>
      {chat.items.length === 0 && (
        <div className="ai-empty">
          <div className="ai-art"><Icon name="sparkles" size={30} /></div>
          <h3>{t("ai.title")}</h3>
          <p className="muted">{t("ai.intro")}</p>
          <div className="ai-suggest">
            {SUGGESTIONS.map((k) => (
              <button key={k} className="suggest-chip" onClick={() => send(t(`ai.${k}`))}>
                <Icon name="sparkles" size={12} /> {t(`ai.${k}`)}
              </button>
            ))}
          </div>
          <p className="muted small">{t("ai.mcpHint")}</p>
          <button className="btn sm ghost mcp-link" onClick={() => useStore.getState().setDialog("mcp")}>
            <Icon name="plug" size={13} /> {t("ai.mcpConnect")}
          </button>
        </div>
      )}
      {chat.items.map((it, i) => <Item key={it.key} item={it} live={chat.running && i === chat.items.length - 1} />)}
      {chat.running && !streaming && last?.kind !== "tool" && (
        <div className="ai-working"><span className="dots"><i /><i /><i /></span> {t("ai.working")}</div>
      )}
    </div>
  );
}

function Item({ item, live }: { item: ChatItem; live: boolean }) {
  const { t } = useTranslation();
  switch (item.kind) {
    case "user":
      return <div className="msg user">{item.text}</div>;
    case "assistant":
      return <div className={`msg assistant ${live ? "live" : ""}`}><Rich text={item.text} /></div>;
    case "thinking":
      return (
        <details className="thinking" open={live}>
          <summary><Icon name="brain" size={13} /> {live ? t("ai.thinkingLive") : t("ai.thinking")}
            {!live && <span className="thinking-preview">{item.text.slice(0, 90)}</span>}
          </summary>
          <div className="thinking-body">{item.text}</div>
        </details>
      );
    case "tool":
      return (
        <div className={`tool-chip ${item.status}`} title={[inputPreview(item.input), item.summary].filter(Boolean).join("\n→ ")}>
          {item.status === "running" ? <span className="mini-spin" /> : <Icon name={item.status === "ok" ? "check" : "close"} size={12} />}
          <span className="tool-name">{item.name}</span>
          <span className="tool-sum">{item.status === "running" ? inputPreview(item.input, 80) : item.summary}</span>
        </div>
      );
    case "image":
      return (
        <figure className="ai-image">
          <img src={item.src} alt={item.caption} onLoad={(e) => {
            // keep the transcript pinned to the bottom once the render has its real height
            const log = e.currentTarget.closest(".ai-log");
            if (log && log.scrollHeight - log.scrollTop - log.clientHeight < e.currentTarget.height + 80) log.scrollTop = log.scrollHeight;
          }} />
          {item.caption && <figcaption title={item.caption}>{item.caption}</figcaption>}
        </figure>
      );
    case "notice":
      return <div className="ai-notice"><Icon name="info" size={13} /> {item.text}</div>;
    case "error":
      return <div className="alert error small">{item.text}</div>;
  }
}

/** Minimal formatting for assistant text: `code`, **bold**, keeps line breaks. No HTML is ever injected. */
function Rich({ text }: { text: string }) {
  const parts = text.split(/(`[^`\n]+`|\*\*[^*\n]+\*\*)/g);
  const out: ReactNode[] = parts.map((p, i) => {
    if (p.startsWith("`") && p.endsWith("`") && p.length > 2) return <code key={i}>{p.slice(1, -1)}</code>;
    if (p.startsWith("**") && p.endsWith("**") && p.length > 4) return <b key={i}>{p.slice(2, -2)}</b>;
    return <Fragment key={i}>{p}</Fragment>;
  });
  return <>{out}</>;
}

// ------------------------------------------------------------------ composer

function Composer({ missing }: { missing: string | null }) {
  const { t } = useTranslation();
  const ai = useAi();
  const prov = currentProvider(ai);
  const [text, setText] = useState("");
  const running = ai.chat.running;
  const blocked = !!missing;

  const submit = () => {
    if (blocked || running || !text.trim()) return;
    ai.send(text);
    setText("");
  };

  return (
    <div className="ai-compose">
      {missing === "key" && prov && (
        <div className="ai-needs">
          <Icon name="key" size={14} /> <span className="grow">{t("ai.needsKey", { provider: prov.name })}</span>
          <button className="btn sm" onClick={() => ai.setSettingsOpen(true)}>{t("ai.setup")}</button>
        </div>
      )}
      <div className={`ai-input ${blocked ? "disabled" : ""}`}>
        <textarea rows={3} value={text} placeholder={t("ai.placeholder")} disabled={blocked}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
              e.preventDefault();
              submit();
            }
          }} />
        {running ? (
          <button className="btn sm danger ai-send" onClick={() => ai.stop()} title={t("ai.stop")}>
            <Icon name="stop" size={13} /> {t("ai.stop")}
          </button>
        ) : (
          <button className="btn sm primary ai-send" disabled={blocked || !text.trim()} onClick={submit} title={t("ai.send")}>
            <Icon name="send" size={13} /> {t("ai.send")}
          </button>
        )}
      </div>
      {prov && <p className="ai-privacy"><Icon name="lock" size={11} /> {t("ai.privacy", { provider: prov.name })}</p>}
    </div>
  );
}
