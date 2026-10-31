// Line breaking for on-screen text (thumbnail title, cards).
// Japanese (line_break "cjk"): break between characters, never before closing punctuation (it hangs on the line
// before) and never after opening punctuation (it moves to the next line); Latin words and numbers stay whole.
// Space languages: greedy word wrap.
//
//   lines('あいうえ「かきくけこ」', 5)                -> ['あいうえ', '「かきくけ', 'こ」']
//   fitTitle(title, 'ja', 2, 10)                     -> {lines (≤ 2), maxChars}: widen until the title fits

export const CLOSING = new Set([...'、。，．」』）】〉》〕］｝！？ー・：；ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮヵヶ!?),.:;']);
export const OPENING = new Set([...'「『（【〈《〔［｛(']);

const UNIT = /[A-Za-z0-9À-ɏ][A-Za-z0-9À-ɏ'’.\-]*|\s+|[\s\S]/gu;

const isSpace = (u: string) => /^\s+$/u.test(u);
const width = (units: string[]) => units.reduce((n, u) => n + [...u].length, 0);

export function lines(text: string, maxChars: number): string[] {
  const units = text.trim().match(UNIT) ?? [];
  const out: string[] = [];
  let cur: string[] = [];
  const flush = () => {
    const l = cur.join('').trim();
    if (l) out.push(l);
  };
  for (const u of units) {
    if (isSpace(u) && cur.length === 0) continue;
    const over = width(cur) + [...u].length > maxChars;
    if (over && cur.length > 0 && !CLOSING.has([...u][0])) {
      const carry: string[] = [];
      while (cur.length && OPENING.has(cur[cur.length - 1])) carry.unshift(cur.pop() as string);
      if (cur.length === 0) {
        cur = carry; // only opening brackets so far: no legal break here
      } else {
        flush();
        cur = carry;
        if (isSpace(u)) continue;
      }
    }
    cur.push(u);
  }
  flush();
  return out;
}

export function wordLines(text: string, maxChars: number): string[] {
  const out: string[] = [];
  let cur = '';
  for (const w of text.trim().split(/\s+/u).filter(Boolean)) {
    if (cur && [...cur].length + 1 + [...w].length > maxChars) {
      out.push(cur);
      cur = w;
    } else {
      cur = cur ? `${cur} ${w}` : w;
    }
  }
  if (cur) out.push(cur);
  return out;
}

export function wrap(text: string, lang: string, maxChars: number): string[] {
  return lang === 'ja' ? lines(text, maxChars) : wordLines(text, maxChars);
}

// The narrowest width (in characters, from startChars up) at which the title fits in maxLines lines.
export function fitTitle(text: string, lang: string, maxLines: number, startChars: number): {lines: string[]; maxChars: number} {
  const total = Math.max([...text].length, startChars);
  for (let n = startChars; n <= total; n++) {
    const ls = wrap(text, lang, n);
    if (ls.length <= maxLines) return {lines: ls, maxChars: n};
  }
  return {lines: wrap(text, lang, total), maxChars: total};
}
