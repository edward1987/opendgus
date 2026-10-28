import { useState } from "react";
import { useTranslation } from "react-i18next";
import { isControl, Item, nextId, reorderItem, removeItems, updateItems } from "../lib/project";
import type { Control, Page } from "../lib/types";
import { currentPage, useStore } from "../store";
import { Icon, WIDGET_ICON } from "./Icons";

export function itemLabel(it: Item): string {
  if (isControl(it)) {
    const p = it.props || {};
    const l = p.label || p.text || "";
    const type = it.type.startsWith("raw:") ? it.type.slice(4) : it.type;
    return l ? `${type} · ${l}` : type + (it.var ? ` · ${it.var}` : "");
  }
  const a = it as any;
  if (a.type === "text") return `"${String(a.text).slice(0, 28)}"`;
  if (a.type === "icon") return `icon · ${a.name}`;
  if (a.type === "image") return `image · ${String(a.src).split("/").pop()}`;
  return a.type;
}

export function itemIcon(it: Item) {
  return WIDGET_ICON[it.type] ?? (it.type.startsWith("raw:") ? "chip" : "shapes");
}

export function LeftPanel() {
  return (
    <aside className="panel left-panel">
      <PagesSection />
      <LayersSection />
    </aside>
  );
}

function PagesSection() {
  const { t } = useTranslation();
  const project = useStore((s) => s.project)!;
  const pageId = useStore((s) => s.pageId);
  const [renaming, setRenaming] = useState<number | null>(null);
  const st = useStore.getState;

  const addPage = () => {
    const id = Math.max(-1, ...project.pages.map((p) => p.id)) + 1;
    const page: Page = { id, name: t("pages.newName", { n: id }), background: { color: "background", gradient: null, image: null }, elements: [], controls: [] };
    st().commit({ ...project, pages: [...project.pages, page] });
    st().setPage(id);
  };

  const duplicate = (pg: Page) => {
    let p = project;
    const id = Math.max(...p.pages.map((x) => x.id)) + 1;
    const copy: Page = structuredClone(pg);
    copy.id = id;
    copy.name = t("pages.copyName", { name: pg.name || `${pg.id}` });
    copy.elements = [];
    copy.controls = [];
    p = { ...p, pages: [...p.pages, copy] };
    for (const e of pg.elements) {
      const n = { ...structuredClone(e), id: nextId(p, "e") };
      copy.elements.push(n);
    }
    for (const c of pg.controls) {
      const n = { ...structuredClone(c), id: nextId(p, "c") } as Control;
      copy.controls.push(n);
    }
    st().commit(p);
    st().setPage(id);
  };

  const remove = (pg: Page) => {
    if (project.pages.length <= 1) return;
    if (!window.confirm(t("pages.confirmDelete", { name: pg.name || pg.id }))) return;
    const pages = project.pages.filter((p) => p.id !== pg.id);
    st().commit({ ...project, pages });
    if (pg.id === pageId) st().setPage(pages[0].id);
  };

  const rename = (pg: Page, name: string) => {
    setRenaming(null);
    if (name !== pg.name) st().commit({ ...project, pages: project.pages.map((p) => (p.id === pg.id ? { ...p, name } : p)) });
  };

  return (
    <section className="panel-section pages">
      <div className="section-head">
        <Icon name="pages" /> <span>{t("pages.title")}</span>
        <div className="spacer" />
        <button className="icon-btn sm" title={t("pages.add")} onClick={addPage}><Icon name="plus" /></button>
      </div>
      <div className="list">
        {project.pages.map((pg) => (
          <div key={pg.id} className={`list-row ${pg.id === pageId ? "selected" : ""}`} onClick={() => st().setPage(pg.id)}
            onDoubleClick={() => setRenaming(pg.id)}>
            <span className="badge">{pg.id}</span>
            {renaming === pg.id ? (
              <input className="inline-input" autoFocus defaultValue={pg.name} onClick={(e) => e.stopPropagation()}
                onBlur={(e) => rename(pg, e.target.value)}
                onKeyDown={(e) => { if (e.key === "Enter") (e.target as HTMLInputElement).blur(); if (e.key === "Escape") setRenaming(null); }} />
            ) : (
              <span className="row-label">{pg.name || t("pages.unnamed")}</span>
            )}
            <span className="row-actions">
              <button className="icon-btn xs" title={t("pages.rename")} onClick={(e) => { e.stopPropagation(); setRenaming(pg.id); }}><Icon name="edit" size={14} /></button>
              <button className="icon-btn xs" title={t("pages.duplicate")} onClick={(e) => { e.stopPropagation(); duplicate(pg); }}><Icon name="copy" size={14} /></button>
              <button className="icon-btn xs" title={t("common.delete")} disabled={project.pages.length <= 1} onClick={(e) => { e.stopPropagation(); remove(pg); }}><Icon name="trash" size={14} /></button>
            </span>
          </div>
        ))}
      </div>
    </section>
  );
}

function LayersSection() {
  const { t } = useTranslation();
  const page = useStore(currentPage);
  const selection = useStore((s) => s.selection);
  const st = useStore.getState;
  if (!page) return null;
  const sel = new Set(selection);

  const row = (it: Item) => (
    <div key={it.id} className={`list-row layer ${sel.has(it.id) ? "selected" : ""} ${it.visible === false ? "hidden-item" : ""}`}
      onClick={(e) => st().select([it.id], e.shiftKey || e.ctrlKey)}>
      <Icon name={itemIcon(it)} size={14} className="layer-icon" />
      <span className="row-label">{itemLabel(it)}</span>
      <span className="row-id">{it.id}</span>
      <span className="row-actions">
        <button className="icon-btn xs" title={t("layers.forward")} onClick={(e) => { e.stopPropagation(); st().commit(reorderItem(st().project!, it.id, 1)); }}><Icon name="up" size={14} /></button>
        <button className="icon-btn xs" title={t("layers.backward")} onClick={(e) => { e.stopPropagation(); st().commit(reorderItem(st().project!, it.id, -1)); }}><Icon name="down" size={14} /></button>
        <button className="icon-btn xs" title={t("common.delete")} onClick={(e) => { e.stopPropagation(); st().commit(removeItems(st().project!, [it.id])); }}><Icon name="trash" size={14} /></button>
      </span>
      <button className={`icon-btn xs vis ${it.visible === false ? "off" : ""}`} title={t("layers.visibility")}
        onClick={(e) => { e.stopPropagation(); st().commit(updateItems(st().project!, [{ ...it, visible: it.visible === false }])); }}>
        <Icon name={it.visible === false ? "eyeOff" : "eye"} size={14} />
      </button>
    </div>
  );

  return (
    <section className="panel-section layers">
      <div className="section-head">
        <Icon name="layers" /> <span>{t("layers.title")}</span>
        <span className="muted small">{page.name}</span>
      </div>
      <div className="list scroll">
        <div className="list-group">{t("layers.controls")} <span className="count">{page.controls.length}</span></div>
        {[...page.controls].reverse().map(row)}
        {page.controls.length === 0 && <div className="list-empty">{t("layers.noControls")}</div>}
        <div className="list-group">{t("layers.elements")} <span className="count">{page.elements.length}</span></div>
        {[...page.elements].reverse().map(row)}
        {page.elements.length === 0 && <div className="list-empty">{t("layers.noElements")}</div>}
      </div>
    </section>
  );
}
