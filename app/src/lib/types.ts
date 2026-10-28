// Mirrors src/opendgus/model.py (kept loose: the backend validates on PUT).

export type Json = null | boolean | number | string | Json[] | { [k: string]: Json };
export type JsonSchema = { [k: string]: any };

export interface Standby {
  enabled: boolean;
  level: number;
  timeout_s: number;
}

export interface Display {
  profile: string | null;
  width: number;
  height: number;
  rotation: 0 | 90 | 180 | 270;
  backlight?: number;
  standby?: Standby;
  [k: string]: any;
}

export interface Screensaver {
  enabled: boolean;
  timeout_s: number;
  page: number | null;
  frame_pages: number[];
  frame_ms: number;
  source: string | null;
  wake_page: number | null;
  brightness: number | null;
}

export interface Theme {
  name: string;
  colors: Record<string, string>;
  font: string;
  font_bold?: string;
  font_light?: string;
  radius: number;
}

export type VarType = "int16" | "uint16" | "int32" | "uint32" | "text" | "bits";

export interface Variable {
  name: string;
  type: VarType;
  vp: number | null;
  init: number | string;
  length: number;
  decimals: number;
  doc: string;
}

export interface BoxItem {
  id: string;
  type: string;
  x: number;
  y: number;
  w: number;
  h: number;
  visible: boolean;
  [k: string]: any;
}

export interface LineElement {
  id: string;
  type: "line";
  points: number[];
  color: string;
  width: number;
  visible: boolean;
}

export type Element = BoxItem | LineElement;

export interface Control extends BoxItem {
  var: string | null;
  props: Record<string, any>;
}

export interface Background {
  color: string | null;
  gradient: string[] | null;
  image: string | null;
}

export interface Page {
  id: number;
  name: string;
  background: Background;
  elements: Element[];
  controls: Control[];
}

export interface Project {
  schema_version: number;
  name: string;
  description: string;
  display: Display;
  theme: Theme;
  variables: Variable[];
  pages: Page[];
  screensaver?: Screensaver;
  controller?: { board: string | null; mqtt: boolean };
}

export interface WidgetInfo {
  type: string;
  title: string;
  category: string;
  description: string;
  needs_var: boolean;
  verified: string;
  props: JsonSchema;
}

export interface DgusControlInfo {
  type: string; // raw:<key>
  title: string;
  kind: string;
  category: string;
  verified: string;
  description: string;
}

export interface Profile {
  id: string;
  width: number;
  height: number;
  diagonal: number | null;
  touch: string;
  flash_mb: number;
  cpu: string;
  series: string;
}

export interface TemplateInfo {
  id: string;
  title: string;
  description: string;
}

export interface Catalog {
  widgets: WidgetInfo[];
  dgus_controls: DgusControlInfo[];
  element_schema: JsonSchema;
  project_schema: JsonSchema;
  profiles: Profile[];
  templates: TemplateInfo[];
}

export interface Box {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface ItemRef {
  item: Element | Control;
  kind: "element" | "control";
  index: number;
}
