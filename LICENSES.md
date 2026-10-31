# License check for Video 1 and the channel (2026-10-22)

Status key: OK = cleared for commercial use on the evidence below; ACTION = must be fixed before monetising; CHECK = not fully verified, decide before publishing.

| Item | What we use | Status | Evidence / action |
|---|---|---|---|
| Font | Patrick Hand (`tools/kit/fonts/`) in every frame, card, avatar, banner | OK | SIL Open Font License 1.1, commercial use allowed; notice in `tools/kit/fonts/LICENSE_PatrickHand.txt`. Replaced Comic Sans MS on 2026-10-22: the macOS copy is not covered by Microsoft's Windows font FAQ, so its terms were unclear. Old Comic Sans frames are only in `_archive/`: do not publish those. |
| Voice-over | ElevenLabs, 10k credits/month (Free plan) | ACTION | ElevenLabs pricing page lists "Commercial License" only from Starter ($6/month, 30k credits). Docs: free-plan output is non-commercial with attribution. Third-party guides say upgrading does not cover audio made before; ElevenLabs' own wording on this was not found. Subscribe to Starter (or higher), regenerate all 10 voice files while subscribed, keep the invoice. Also check the chosen voice's own terms in the Voice Library. |
| Edge extension for ElevenLabs | Automates the ElevenLabs web page | CHECK | ElevenLabs terms on automating the web app were not read. Read them; if automation is not allowed, generate by hand or use their API. |
| Data | BLS, Census ACS, IRS, CRS figures; FRED series; Census Reporter as a reader of ACS data | OK (cite) | Works of the US federal government are not protected by copyright (17 U.S.C. 105). FRED's legal page was down for maintenance when checked; the series used come from BLS. Cite sources (done in description and frame 10_06). |
| Drawings | Stick figure, props, charts, cards, avatar, banner, all drawn by our own code | OK | No third-party images, logos or clips. Note: images made with AI help may get weak or no copyright protection, so others might copy them; that does not limit our own use. |
| Reference storyboards | `_archive/visuals/ref/` (old layout, removed in the 2026-10-23 cleanup) (Hawk, EverythingProfessor, Productive Peter, Explains 101) | OK if not published | Used only to study style. Never put them in a video or thumbnail. Safe to delete. |
| Script | Our own text | OK | No quotes from other sources. |
| CapCut | Editing | CHECK | Third-party reports: CapCut's built-in music is not licensed for commercial use and is often claimed by Content ID; some effects/templates are non-commercial. Use only our images, our voice, and separately licensed music; avoid CapCut library audio/templates. CapCut's terms also give CapCut a licence to content you make there; read the current ToS. |
| Music | Not chosen | CHECK | Use YouTube Audio Library or another licence that allows monetised YouTube; record track name and licence (some need attribution). |
| YouTube AI disclosure | Synthetic narrator voice | CHECK | YouTube help: disclosure needed for realistic altered/synthetic content, e.g. synthetically generating a person's voice to narrate. No official line found for a generic AI voice that imitates nobody. Safe option: tick the disclosure box in Studio. |
| Channel name | "The Median Worker" | CHECK | No YouTube channel with that name found in search. Trademark not checked: search USPTO before investing in the brand. |
| Python, Edge headless | Rendering tools | OK | No licence claim on output images. |
| Remotion 4.0.537 (`tools/anim/`) | Animated video renderer (React) | CHECK | Remotion License (in `tools/anim/node_modules/remotion/LICENSE.md`): free, including commercial videos, for an individual or a for-profit company with up to 3 employees; larger companies need a paid Company License (remotion.pro). OK if the channel is run by the owner personally; if it is run by or for a company with more than 3 employees, buy the Company License before publishing videos made with it. |

Evidence links: ElevenLabs pricing https://elevenlabs.io/pricing ; Microsoft font FAQ https://learn.microsoft.com/en-us/typography/fonts/font-faq ; YouTube disclosure https://support.google.com/youtube/answer/14328491 ; Patrick Hand https://github.com/google/fonts/tree/main/ofl/patrickhand

## Japanese font: Noto Sans JP (Plan 6, 2026-11-01)

- File: `tools/kit/fonts/NotoSansJP-Variable.ttf` (variable weight 100–900; renamed from `NotoSansJP[wght].ttf`), used for ja on-screen text and thumbnails.
- Downloaded from https://github.com/google/fonts/raw/main/ofl/notosansjp/NotoSansJP%5Bwght%5D.ttf (folder https://github.com/google/fonts/tree/main/ofl/notosansjp) on 2026-11-01.
- SHA-256: `c2f3b4d463500a2ddcd3849cded1fceeb9fd6d1c32e6cbecd568453ba50fc68f`
- Licence: SIL Open Font License 1.1 (`OFL.txt` in the same folder: "Copyright 2014-2021 Adobe (http://www.adobe.com/), with Reserved Font Name 'Source'"). Commercial use and embedding in videos/images allowed; the font itself must not be sold alone. Status: OK.
