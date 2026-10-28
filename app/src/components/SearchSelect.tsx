// Searchable dropdown (select2-style) for long lists such as a provider's models. The list opens in a portal
// so it is not clipped by scrolling panels. Typing a value that is not listed offers it as a custom entry.
import { ReactNode, useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Icon } from "./Icons";

export interface SearchOption {
  value: string;
  label: string;
  /** extra words to match (e.g. the display name) */
  search?: string;
  /** right-aligned detail (e.g. price) */
  detail?: ReactNode;
}

interface Props {
  value: string;
  options: SearchOption[];
  onChange(value: string): void;
  placeholder?: string;
  searchPlaceholder?: string;
  emptyText?: string;
  /** label of the "use what I typed" entry, e.g. 'Use "{value}"' */
  customLabel?: (typed: string) => string;
  disabled?: boolean;
}

const MAX_SHOWN = 300;

export function SearchSelect({ value, options, onChange, placeholder, searchPlaceholder, emptyText, customLabel, disabled }: Props) {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [active, setActive] = useState(0);
  const [rect, setRect] = useState<DOMRect | null>(null);
  const btn = useRef<HTMLButtonElement>(null);
  const pop = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLDivElement>(null);

  const q = query.trim().toLowerCase();
  const filtered = useMemo(() => {
    if (!q) return options;
    const words = q.split(/\s+/);
    return options.filter((o) => {
      const hay = `${o.value} ${o.label} ${o.search ?? ""}`.toLowerCase();
      return words.every((w) => hay.includes(w));
    });
  }, [options, q]);
  const custom = customLabel && query.trim() && !options.some((o) => o.value === query.trim()) ? query.trim() : null;
  const rows: (SearchOption & { custom?: boolean })[] = [
    ...(custom ? [{ value: custom, label: customLabel!(custom), custom: true }] : []),
    ...filtered.slice(0, MAX_SHOWN),
  ];
  const current = options.find((o) => o.value === value);

  const place = () => btn.current && setRect(btn.current.getBoundingClientRect());
  const close = () => { setOpen(false); setQuery(""); };
  const pick = (v: string) => { onChange(v); close(); btn.current?.focus(); };

  useLayoutEffect(() => {
    if (!open) return;
    place();
    const i = rows.findIndex((r) => r.value === value);
    setActive(Math.max(0, i));
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const down = (e: MouseEvent) => {
      if (!pop.current?.contains(e.target as Node) && !btn.current?.contains(e.target as Node)) close();
    };
    const scroll = (e: Event) => { if (!pop.current?.contains(e.target as Node)) place(); };
    document.addEventListener("mousedown", down);
    window.addEventListener("resize", place);
    window.addEventListener("scroll", scroll, true);
    return () => {
      document.removeEventListener("mousedown", down);
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", scroll, true);
    };
  }, [open]);

  useEffect(() => { setActive(0); }, [q]);
  useEffect(() => {
    list.current?.querySelector<HTMLElement>(`[data-i="${active}"]`)?.scrollIntoView({ block: "nearest" });
  }, [active, open]);

  const onKey = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") { e.preventDefault(); setActive((a) => Math.min(rows.length - 1, a + 1)); }
    else if (e.key === "ArrowUp") { e.preventDefault(); setActive((a) => Math.max(0, a - 1)); }
    else if (e.key === "PageDown") { e.preventDefault(); setActive((a) => Math.min(rows.length - 1, a + 10)); }
    else if (e.key === "PageUp") { e.preventDefault(); setActive((a) => Math.max(0, a - 10)); }
    else if (e.key === "Enter") { e.preventDefault(); if (rows[active]) pick(rows[active].value); }
    else if (e.key === "Escape") { e.preventDefault(); e.stopPropagation(); close(); btn.current?.focus(); }
    else if (e.key === "Tab") close();
  };

  // open upwards when there is not enough room below
  const below = rect ? window.innerHeight - rect.bottom : 0;
  const up = !!rect && below < 280 && rect.top > below;
  const style: React.CSSProperties = rect
    ? { left: rect.left, width: Math.max(rect.width, 280), ...(up ? { bottom: window.innerHeight - rect.top + 4 } : { top: rect.bottom + 4 }),
        maxHeight: Math.max(160, (up ? rect.top : below) - 12) }
    : { display: "none" };

  return (
    <>
      <button ref={btn} type="button" className="search-select" disabled={disabled}
        onClick={() => (open ? close() : setOpen(true))}
        onKeyDown={(e) => { if (!open && (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ")) { e.preventDefault(); setOpen(true); } }}>
        <span className={`grow ellipsis ${value ? "mono" : "muted"}`}>{value || placeholder}</span>
        {current?.detail && <span className="search-select-detail">{current.detail}</span>}
        <Icon name="down" size={12} />
      </button>
      {open && createPortal(
        <div ref={pop} className="search-select-pop" style={style} onKeyDown={onKey}>
          <div className="search-select-q">
            <Icon name="search" size={13} />
            <input autoFocus spellCheck={false} value={query} placeholder={searchPlaceholder} onChange={(e) => setQuery(e.target.value)} />
            <span className="muted small">{filtered.length}</span>
          </div>
          <div className="search-select-list" ref={list} role="listbox">
            {rows.length === 0 && <div className="search-select-empty muted small">{emptyText}</div>}
            {rows.map((r, i) => (
              <div key={(r.custom ? "custom:" : "") + r.value} data-i={i} role="option" aria-selected={r.value === value}
                className={`search-select-opt ${i === active ? "active" : ""} ${r.value === value && !r.custom ? "selected" : ""}`}
                onMouseEnter={() => setActive(i)} onMouseDown={(e) => { e.preventDefault(); pick(r.value); }}>
                <div className="grow ellipsis">
                  <div className={`ellipsis ${r.custom ? "" : "mono"}`}>{r.custom ? r.label : r.value}</div>
                  {!r.custom && r.label !== r.value && <div className="muted small ellipsis">{r.label}</div>}
                </div>
                {r.detail && <span className="search-select-detail">{r.detail}</span>}
              </div>
            ))}
            {filtered.length > MAX_SHOWN && <div className="search-select-empty muted small">+{filtered.length - MAX_SHOWN}…</div>}
          </div>
        </div>,
        document.body,
      )}
    </>
  );
}
