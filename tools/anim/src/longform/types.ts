// Props of the Longform composition, as written by tools/longform/render.py props() (paths are relative to the
// staged public folder). Shapes follow scenes/scenes.json (tools/longform/scenes.py).
import type {Anchors, Cam, Timing} from './timeline';
import type {Faction} from './factions';

export type Labels = Record<string, Record<string, string>>;
export type HeroSpec = {key: string; x: number; enter?: 'left' | 'right' | 'none'; keys?: {sentence: string; key: string}[]};
export type CrowdSpec = {faction: Faction; count: number; path: 'background' | [number, number][]; speed: number};
export type CardSpec = {type: 'date' | 'name' | 'two_source' | 'chapter'; sentence: string; text_key: string; text_key2?: string};
export type MapSpec = {
  bbox: [number, number, number, number];
  places?: {label_key: string; lon: number; lat: number}[];
  arrows?: {from: [number, number]; to: [number, number]; sentence: string}[];
  areas?: {points: [number, number][]; fact: string | null; type?: 'area' | 'border'}[];
};
export type SfxSpec = {sentence: string; id: string; offset?: number; gain: number};
export type BeatSpec = {
  background: {id: string; camera: {from: Cam; to: Cam}};
  heroes?: HeroSpec[]; crowds?: CrowdSpec[]; cards?: CardSpec[]; map?: MapSpec | null; sfx?: SfxSpec[];
};
export type ScenesDoc = {chapters: {id: string; music: string | null; title_card?: boolean}[]; beats: Record<string, BeatSpec>};
export type BgInfo = {image: string; horizonY?: number | null; groundY?: number | null; heroGround?: number | null; path?: [number, number][]};
export type ChapterInfo = {id: string; title: string; beats: string[]; titleCard: boolean};
export type AudioProps = {voice: {file: string; start: number}[]; music: Record<string, string>; sfx: {id: string; file: string}[]};
export type FontInfo = {family: string; file: string};

export type LongformProps = {
  scenes: ScenesDoc; timing: Timing; labels: Labels; lang: string; audio: AudioProps;
  chapters: ChapterInfo[]; anchors: Anchors; backgrounds: Record<string, BgInfo>; font: FontInfo;
};

export const label = (labels: Labels, key: string | undefined, lang: string): string => (key ? labels[key]?.[lang] ?? '' : '');
