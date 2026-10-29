// JSON schema (pydantic flavour) -> form field descriptors for the Properties panel. Pure (unit tested).
import type { JsonSchema } from "./types";

export type FieldKind =
  | "string"
  | "integer"
  | "number"
  | "boolean"
  | "enum"
  | "color"
  | "icon"
  | "object"
  | "union"
  | "array"
  | "colorList"
  | "stringList"
  | "intList"
  | "json";

export interface EnumOption {
  value: string | number;
  label: string;
}

export interface Variant {
  tag: string;
  label: string;
  fields: FieldDesc[];
  schema: JsonSchema;
}

export interface FieldDesc {
  key: string;
  label: string;
  description?: string;
  kind: FieldKind;
  nullable: boolean;
  required: boolean;
  default?: unknown;
  enum?: EnumOption[];
  min?: number;
  max?: number;
  unit?: string;
  advanced?: boolean;
  fields?: FieldDesc[]; // object
  discriminator?: string; // union
  variants?: Variant[]; // union
  item?: FieldDesc; // array of objects
  itemSchema?: JsonSchema;
}

export interface MapOptions {
  root?: JsonSchema; // where $defs live (defaults to the schema itself)
  exclude?: string[];
  iconKeys?: string[]; // string keys edited with the icon picker (default: "icon")
}

const COLOR_KEY = /(^|_)(color|colour|fill|stroke|track|knob|background)$/;

export function humanize(key: string): string {
  const s = key.replace(/_/g, " ").trim();
  return s.charAt(0).toUpperCase() + s.slice(1);
}

export function resolveRef(s: JsonSchema, root: JsonSchema): JsonSchema {
  let cur = s;
  for (let i = 0; i < 10 && cur && typeof cur.$ref === "string"; i++) {
    const name = cur.$ref.replace(/^#\/(\$defs|definitions)\//, "");
    const target = root.$defs?.[name] ?? root.definitions?.[name];
    if (!target) break;
    const { $ref: _ignored, ...rest } = cur;
    cur = { ...target, ...rest };
  }
  return cur;
}

/** Strip a `null` alternative: anyOf [X, {type:null}] -> X (nullable). */
export function unwrapNullable(s: JsonSchema, root: JsonSchema): { schema: JsonSchema; nullable: boolean } {
  const alts: JsonSchema[] | undefined = s.anyOf ?? (Array.isArray(s.type) ? undefined : undefined);
  if (alts) {
    const nonNull = alts.filter((a) => a.type !== "null");
    if (nonNull.length < alts.length) {
      const { anyOf: _a, ...rest } = s;
      const inner = nonNull.length === 1 ? { ...resolveRef(nonNull[0], root), ...pick(rest) } : { ...rest, anyOf: nonNull };
      return { schema: inner, nullable: true };
    }
  }
  if (Array.isArray(s.type) && s.type.includes("null")) {
    const t = s.type.filter((x: string) => x !== "null");
    return { schema: { ...s, type: t.length === 1 ? t[0] : t }, nullable: true };
  }
  return { schema: resolveRef(s, root), nullable: false };
}

function pick(rest: JsonSchema): JsonSchema {
  const out: JsonSchema = {};
  for (const k of ["title", "description", "default"]) if (k in rest) out[k] = rest[k];
  return out;
}

function variantsOf(s: JsonSchema, root: JsonSchema, opts: MapOptions): { disc: string; variants: Variant[] } | null {
  const alts: JsonSchema[] | undefined = s.oneOf ?? s.anyOf;
  if (!alts || !alts.length) return null;
  const resolved = alts.map((a) => resolveRef(a, root));
  if (!resolved.every((r) => r.type === "object" || r.properties)) return null;
  const disc: string = s.discriminator?.propertyName ?? "type";
  if (!resolved.every((r) => r.properties?.[disc]?.const !== undefined || r.properties?.[disc]?.default !== undefined))
    return null;
  return {
    disc,
    variants: resolved.map((r) => {
      const tag = String(r.properties[disc].const ?? r.properties[disc].default);
      return {
        tag,
        label: r.title ? humanize(String(r.title).replace(/Action$/, "")) : humanize(tag),
        fields: schemaToFields(r, { ...opts, root, exclude: [disc] }),
        schema: r,
      };
    }),
  };
}

export function fieldFromSchema(key: string, raw: JsonSchema, required: boolean, opts: MapOptions): FieldDesc {
  const root = opts.root ?? raw;
  const { schema: s, nullable } = unwrapNullable(raw, root);
  const base: FieldDesc = {
    key,
    label: raw.title ?? s.title ?? humanize(key),
    description: raw.description ?? s.description,
    kind: "json",
    nullable: nullable || raw.default === null,
    required,
    default: raw.default ?? s.default,
    min: s.minimum ?? s.min,
    max: s.maximum ?? s.max,
    unit: s.unit,
    advanced: !!(raw.advanced ?? s.advanced),
  };
  const iconKeys = opts.iconKeys ?? ["icon"];

  if (Array.isArray(s.enum)) {
    const names: string[] | undefined = s.enumNames;
    return { ...base, kind: "enum", enum: s.enum.map((v: string | number, i: number) => ({ value: v, label: names?.[i] ?? String(v) })) };
  }
  if (s.const !== undefined) return { ...base, kind: "enum", enum: [{ value: s.const, label: String(s.const) }] };

  const union = variantsOf(s, root, opts);
  if (union) return { ...base, kind: "union", discriminator: union.disc, variants: union.variants };

  switch (s.type) {
    case "string":
      if (iconKeys.includes(key)) return { ...base, kind: "icon" };
      if (COLOR_KEY.test(key)) return { ...base, kind: "color" };
      return { ...base, kind: "string" };
    case "integer":
      return { ...base, kind: "integer" };
    case "number":
      return { ...base, kind: "number" };
    case "boolean":
      return { ...base, kind: "boolean" };
    case "object":
      if (s.properties) return { ...base, kind: "object", fields: schemaToFields(s, { ...opts, root, exclude: [] }) };
      return base;
    case "array": {
      const item = s.items ? unwrapNullable(s.items, root).schema : {};
      if (item.type === "integer" || item.type === "number") return { ...base, kind: "intList" };
      if (item.type === "string") return { ...base, kind: COLOR_KEY.test(key) || key === "gradient" ? "colorList" : "stringList" };
      if (item.type === "object" || item.properties)
        return {
          ...base,
          kind: "array",
          itemSchema: item,
          item: { ...base, key: "item", kind: "object", fields: schemaToFields(item, { ...opts, root, exclude: [] }) },
        };
      return base;
    }
  }
  return base;
}

/** All fields of an object schema, in declaration order, minus `exclude`. */
export function schemaToFields(schema: JsonSchema, opts: MapOptions = {}): FieldDesc[] {
  const root = opts.root ?? schema;
  const s = resolveRef(schema, root);
  const props: Record<string, JsonSchema> = s.properties ?? {};
  const required: string[] = s.required ?? [];
  const exclude = new Set(opts.exclude ?? []);
  return Object.entries(props)
    .filter(([k]) => !exclude.has(k))
    .map(([k, v]) => fieldFromSchema(k, v, required.includes(k), { ...opts, root }));
}

/** A starting value for a new object of `schema` (defaults, plus zero values for required fields). */
export function defaultObject(schema: JsonSchema, root: JsonSchema = schema): Record<string, unknown> {
  const s = resolveRef(schema, root);
  const out: Record<string, unknown> = {};
  const required: string[] = s.required ?? [];
  for (const [k, raw] of Object.entries<JsonSchema>(s.properties ?? {})) {
    const v = raw.const ?? raw.default;
    if (v !== undefined) out[k] = v;
    else if (required.includes(k)) {
      const t = unwrapNullable(raw, root).schema;
      out[k] = t.type === "integer" || t.type === "number" ? 0 : t.type === "boolean" ? false : t.type === "array" ? [] : "";
    }
  }
  return out;
}

/** Raw DGUS spec schema (opendgus.formats.spec.schema) -> JSON-schema object, hiding geometry/vp handled by the control. */
export const RAW_HIDDEN = ["x", "y", "x1", "y1", "x2", "y2", "page", "vp"];

export function rawSpecToSchema(spec: { properties: Record<string, JsonSchema> }): JsonSchema {
  const properties: Record<string, JsonSchema> = {};
  for (const [k, p] of Object.entries(spec.properties ?? {})) {
    if (RAW_HIDDEN.includes(k)) continue;
    properties[k] = { ...p, title: humanize(k) };
  }
  return { type: "object", properties };
}

/** Split fields into basic and advanced. */
export function splitAdvanced(fields: FieldDesc[]): [FieldDesc[], FieldDesc[]] {
  return [fields.filter((f) => !f.advanced), fields.filter((f) => f.advanced)];
}
