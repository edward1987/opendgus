// Form controls used by the schema-driven Properties panel.
import { ReactNode, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { defaultObject, FieldDesc } from "../lib/schemaForm";
import { useStore } from "../store";
import { Icon } from "./Icons";

const NO_COLORS: Record<string, string> = {};
const NO_VARS: never[] = [];

export type OnChange = (v: unknown) => void;

export function Row({ label, hint, children, wide }: { label: ReactNode; hint?: string; children: ReactNode; wide?: boolean }) {
  return (
    <label className={`prop-row ${wide ? "wide" : ""}`} title={hint}>
      <span className="prop-label">{label}</span>
      <span className="prop-input">{children}</span>
    </label>
  );
}

export function NumberInput({ value, onChange, min, max, step, placeholder, nullable, integer = true }: {
  value: number | null | undefined;
  onChange: (v: number | null) => void;
  min?: number;
  max?: number;
  step?: number;
  placeholder?: string;
  nullable?: boolean;
  integer?: boolean;
}) {
  const [text, setText] = useState(value === null || value === undefined ? "" : String(value));
  const focused = useRef(false);
  useEffect(() => {
    if (!focused.current) setText(value === null || value === undefined ? "" : String(value));
  }, [value]);
  return (
    <input type="number" value={text} min={min} max={max} step={step ?? (integer ? 1 : 0.05)} placeholder={placeholder}
      onFocus={() => (focused.current = true)}
      onBlur={() => { focused.current = false; setText(value === null || value === undefined ? "" : String(value)); }}
      onChange={(e) => {
        setText(e.target.value);
        if (e.target.value.trim() === "") {
          if (nullable) onChange(null);
          return;
        }
        let n = Number(e.target.value);
        if (!Number.isFinite(n)) return;
        if (integer) n = Math.round(n);
        if (min !== undefined && n < min) return;
        if (max !== undefined && n > max) return;
        onChange(n);
      }} />
  );
}

export function Switch({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button type="button" role="switch" aria-checked={checked} className={`switch ${checked ? "on" : ""}`} onClick={() => onChange(!checked)}>
      <span />
    </button>
  );
}

function usePopover() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const h = (e: MouseEvent) => { if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false); };
    window.addEventListener("mousedown", h);
    return () => window.removeEventListener("mousedown", h);
  }, [open]);
  return { open, setOpen, ref };
}

export function ColorField({ value, onChange, nullable }: { value: string | null | undefined; onChange: (v: string | null) => void; nullable?: boolean }) {
  const { t } = useTranslation();
  const colors = useStore((s) => s.project?.theme.colors ?? NO_COLORS);
  const { open, setOpen, ref } = usePopover();
  const resolved = value ? (value.startsWith("#") ? value : colors[value]) : null;
  const [hex, setHex] = useState(resolved ?? "#ffffff");
  useEffect(() => setHex(resolved ?? "#ffffff"), [resolved]);
  return (
    <div className="color-field" ref={ref}>
      <button type="button" className="color-btn" onClick={() => setOpen(!open)}>
        <span className={`swatch ${resolved ? "" : "none"}`} style={{ background: resolved ?? undefined }} />
        <span className="color-name">{value ? value : nullable ? t("fields.auto") : t("fields.none")}</span>
        <Icon name="down" size={12} />
      </button>
      {open && (
        <div className="popover color-pop">
          <div className="pop-title">{t("fields.themeTokens")}</div>
          <div className="token-grid">
            {Object.entries(colors).map(([k, c]) => (
              <button key={k} type="button" className={`token ${value === k ? "on" : ""}`} title={`${k} ${c}`} onClick={() => { onChange(k); setOpen(false); }}>
                <span className="swatch" style={{ background: c }} />
                <span>{k}</span>
              </button>
            ))}
          </div>
          <div className="pop-title">{t("fields.custom")}</div>
          <div className="row gap">
            <input type="color" value={/^#[0-9a-fA-F]{6}$/.test(hex) ? hex : "#ffffff"} onChange={(e) => { setHex(e.target.value.toUpperCase()); onChange(e.target.value.toUpperCase()); }} />
            <input className="grow mono" value={hex} onChange={(e) => { setHex(e.target.value); if (/^#[0-9a-fA-F]{6}$/.test(e.target.value)) onChange(e.target.value.toUpperCase()); }} />
          </div>
          {nullable && <button type="button" className="btn sm ghost full" onClick={() => { onChange(null); setOpen(false); }}>{t("fields.auto")}</button>}
        </div>
      )}
    </div>
  );
}

export function IconField({ value, onChange, nullable }: { value: string | null | undefined; onChange: (v: string | null) => void; nullable?: boolean }) {
  const { t } = useTranslation();
  const api = useStore((s) => s.api);
  const { open, setOpen, ref } = usePopover();
  const [q, setQ] = useState("");
  const [hits, setHits] = useState<string[]>([]);
  useEffect(() => {
    if (!open || !api) return;
    const query = q.trim() || value || "home";
    const h = setTimeout(() => {
      api.tool<string[]>("search_icons", { query, limit: 80 }).then(setHits).catch(() => setHits([]));
    }, 150);
    return () => clearTimeout(h);
  }, [q, open, api]);
  return (
    <div className="icon-field" ref={ref}>
      <button type="button" className="color-btn" onClick={() => setOpen(!open)}>
        {value && api ? <img className="glyph sm" src={api.iconUrl(value, 32)} alt="" /> : <Icon name="star" size={14} />}
        <span className="color-name">{value || t("fields.none")}</span>
        <Icon name="search" size={12} />
      </button>
      {open && (
        <div className="popover icon-pop">
          <div className="search">
            <Icon name="search" />
            <input autoFocus placeholder={t("fields.searchIcons")} value={q} onChange={(e) => setQ(e.target.value)} />
          </div>
          <div className="icon-hits">
            {hits.map((n) => (
              <button key={n} type="button" title={n} className={`icon-hit ${n === value ? "on" : ""}`} onClick={() => { onChange(n); setOpen(false); }}>
                {api && <img className="glyph" src={api.iconUrl(n, 48, n === value ? "#04121D" : "#E2E8F0")} alt="" loading="lazy" />}
                <span>{n}</span>
              </button>
            ))}
            {hits.length === 0 && <span className="muted small">{t("fields.noIcons")}</span>}
          </div>
          {nullable && value && <button type="button" className="btn sm ghost full" onClick={() => { onChange(null); setOpen(false); }}>{t("fields.removeIcon")}</button>}
        </div>
      )}
    </div>
  );
}

export function VarField({ value, onChange, onCreate }: { value: string | null; onChange: (v: string | null) => void; onCreate: (name: string, type: string) => void }) {
  const { t } = useTranslation();
  const vars = useStore((s) => s.project?.variables ?? NO_VARS);
  const [creating, setCreating] = useState(false);
  const [name, setName] = useState("");
  const [type, setType] = useState("int16");
  const valid = /^[A-Za-z_][A-Za-z0-9_]*$/.test(name) && !vars.some((v) => v.name === name);
  if (creating)
    return (
      <div className="var-create">
        <input autoFocus placeholder={t("vars.name")} value={name} onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter" && valid) { onCreate(name, type); setCreating(false); setName(""); } }} />
        <select value={type} onChange={(e) => setType(e.target.value)}>
          {["int16", "uint16", "int32", "uint32", "text", "bits"].map((x) => <option key={x}>{x}</option>)}
        </select>
        <button type="button" className="btn sm primary" disabled={!valid} onClick={() => { onCreate(name, type); setCreating(false); setName(""); }}>{t("common.add")}</button>
        <button type="button" className="icon-btn xs" onClick={() => setCreating(false)}><Icon name="close" size={14} /></button>
      </div>
    );
  return (
    <select value={value ?? ""} onChange={(e) => (e.target.value === "__new" ? setCreating(true) : onChange(e.target.value || null))}>
      <option value="">{t("fields.noVar")}</option>
      {vars.map((v) => <option key={v.name} value={v.name}>{v.name} ({v.type})</option>)}
      <option value="__new">{t("fields.newVar")}</option>
    </select>
  );
}

// ------------------------------------------------------------------ schema-driven form

export function SchemaForm({ fields, value, onChange }: { fields: FieldDesc[]; value: Record<string, any>; onChange: (v: Record<string, any>, key: string) => void }) {
  return (
    <>
      {fields.map((f) => (
        <FieldEditor key={f.key} field={f} value={value?.[f.key]}
          onChange={(v) => {
            const next = { ...(value || {}) };
            if (v === undefined) delete next[f.key];
            else next[f.key] = v;
            onChange(next, f.key);
          }} />
      ))}
    </>
  );
}

export function FieldEditor({ field: f, value, onChange }: { field: FieldDesc; value: any; onChange: OnChange }) {
  const { t } = useTranslation();
  const v = value === undefined ? f.default : value;
  const label = t(`fieldNames.${f.key}`, { defaultValue: f.label });
  const hint = f.description;
  switch (f.kind) {
    case "string":
      return <Row label={label} hint={hint}><input value={v ?? ""} placeholder={f.nullable ? t("fields.auto") : ""} onChange={(e) => onChange(f.nullable && e.target.value === "" ? null : e.target.value)} /></Row>;
    case "integer":
    case "number":
      return (
        <Row label={label} hint={hint}>
          <NumberInput value={v} nullable={f.nullable} min={f.min} max={f.max} integer={f.kind === "integer"}
            placeholder={f.nullable ? t("fields.auto") : ""} onChange={(n) => onChange(n)} />
          {f.unit && <span className="unit">{f.unit}</span>}
        </Row>
      );
    case "boolean":
      return <Row label={label} hint={hint}><Switch checked={!!v} onChange={onChange} /></Row>;
    case "enum":
      return (
        <Row label={label} hint={hint}>
          <select value={v === null || v === undefined ? "" : String(v)}
            onChange={(e) => {
              if (e.target.value === "") return onChange(null);
              const opt = f.enum!.find((o) => String(o.value) === e.target.value);
              onChange(opt?.value);
            }}>
            {(f.nullable || v === undefined || v === null) && <option value="">{f.nullable ? t("fields.auto") : "—"}</option>}
            {f.enum!.map((o) => <option key={String(o.value)} value={String(o.value)}>{t(`enum.${o.label}`, { defaultValue: o.label })}</option>)}
          </select>
        </Row>
      );
    case "color":
      return <Row label={label} hint={hint}><ColorField value={v} nullable={f.nullable} onChange={onChange} /></Row>;
    case "icon":
      return <Row label={label} hint={hint}><IconField value={v} nullable={f.nullable} onChange={onChange} /></Row>;
    case "intList":
      return (
        <Row label={label} hint={hint}>
          <ListText value={Array.isArray(v) ? v : []} onChange={onChange} />
        </Row>
      );
    case "colorList": {
      const list: string[] = Array.isArray(v) ? v : [];
      return (
        <div className="prop-block">
          <div className="prop-block-head">
            <span>{label}</span>
            <button type="button" className="icon-btn xs" title={t("common.add")} onClick={() => onChange([...list, list[list.length - 1] ?? "primary"])}><Icon name="plus" size={14} /></button>
            {f.nullable && list.length > 0 && <button type="button" className="icon-btn xs" title={t("fields.clear")} onClick={() => onChange(null)}><Icon name="close" size={14} /></button>}
          </div>
          {list.map((c, i) => (
            <div key={i} className="row gap">
              <ColorField value={c} onChange={(nv) => onChange(list.map((x, j) => (j === i ? nv ?? x : x)))} />
              <button type="button" className="icon-btn xs" onClick={() => { const nl = list.filter((_, j) => j !== i); onChange(nl.length ? nl : f.nullable ? null : []); }}><Icon name="trash" size={14} /></button>
            </div>
          ))}
        </div>
      );
    }
    case "stringList": {
      const list: string[] = Array.isArray(v) ? v : [];
      return (
        <div className="prop-block">
          <div className="prop-block-head">
            <span>{label}</span>
            <button type="button" className="icon-btn xs" title={t("common.add")} onClick={() => onChange([...list, "Option"])}><Icon name="plus" size={14} /></button>
          </div>
          {list.map((item, i) => (
            <div key={i} className="row gap">
              <input value={item} onChange={(e) => onChange(list.map((x, j) => j === i ? e.target.value : x))} />
              <button type="button" className="icon-btn xs" onClick={() => onChange(list.filter((_, j) => j !== i))}><Icon name="trash" size={14} /></button>
            </div>
          ))}
        </div>
      );
    }
    case "object":
      return (
        <fieldset className="prop-block">
          <legend>{label}</legend>
          <SchemaForm fields={f.fields ?? []} value={v ?? {}} onChange={(nv) => onChange(nv)} />
        </fieldset>
      );
    case "union": {
      const tag = v?.[f.discriminator!];
      const variant = f.variants!.find((x) => x.tag === tag);
      return (
        <fieldset className="prop-block">
          <legend>{label}</legend>
          <Row label={t("fields.kind")}>
            <select value={tag ?? ""} onChange={(e) => {
              const nv = f.variants!.find((x) => x.tag === e.target.value);
              onChange(nv ? { ...defaultObject(nv.schema), [f.discriminator!]: nv.tag } : null);
            }}>
              {f.nullable && <option value="">{t("fields.none")}</option>}
              {f.variants!.map((x) => <option key={x.tag} value={x.tag}>{t(`enum.${x.tag}`, { defaultValue: x.label })}</option>)}
            </select>
          </Row>
          {variant && <SchemaForm fields={variant.fields} value={v} onChange={(nv) => onChange({ ...nv, [f.discriminator!]: variant.tag })} />}
        </fieldset>
      );
    }
    case "array": {
      const list: any[] = Array.isArray(v) ? v : [];
      return (
        <div className="prop-block">
          <div className="prop-block-head">
            <span>{label}</span>
            <button type="button" className="icon-btn xs" title={t("common.add")} onClick={() => onChange([...list, defaultObject(f.itemSchema ?? {})])}><Icon name="plus" size={14} /></button>
          </div>
          {list.map((item, i) => (
            <fieldset key={i} className="prop-block nested">
              <legend>
                #{i}
                <button type="button" className="icon-btn xs" onClick={() => onChange(list.filter((_, j) => j !== i))}><Icon name="trash" size={12} /></button>
              </legend>
              <SchemaForm fields={f.item?.fields ?? []} value={item} onChange={(nv) => onChange(list.map((x, j) => (j === i ? nv : x)))} />
            </fieldset>
          ))}
        </div>
      );
    }
    default:
      return <Row label={label} hint={hint} wide><JsonText value={v} onChange={onChange} /></Row>;
  }
}

function ListText({ value, onChange }: { value: number[]; onChange: OnChange }) {
  const [text, setText] = useState(value.join(", "));
  useEffect(() => setText(value.join(", ")), [value.join(",")]);
  return (
    <input className="mono" value={text} onChange={(e) => {
      setText(e.target.value);
      const nums = e.target.value.split(/[\s,;]+/).filter(Boolean).map(Number);
      if (nums.length >= 2 && nums.every(Number.isFinite)) onChange(nums.map(Math.round));
    }} />
  );
}

function JsonText({ value, onChange }: { value: unknown; onChange: OnChange }) {
  const [text, setText] = useState(JSON.stringify(value ?? null));
  const [bad, setBad] = useState(false);
  return (
    <input className={`mono ${bad ? "invalid" : ""}`} value={text} onChange={(e) => {
      setText(e.target.value);
      try {
        onChange(JSON.parse(e.target.value));
        setBad(false);
      } catch {
        setBad(true);
      }
    }} />
  );
}
