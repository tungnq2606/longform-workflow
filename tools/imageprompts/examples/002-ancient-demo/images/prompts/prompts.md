# Prompt pack: Ancient demo

Style: stickman-v1. Tạo ảnh theo đúng thứ tự dưới đây. Các bảng nhân vật (model sheet, cast sheet) phải được duyệt trước khi tạo cảnh.

Cách làm tay (khi không chạy tự động bằng Gemini CLI):
- Google Flow: chọn Image, model Nano Banana Pro (hoặc 2.1), tỉ lệ 16:9. Không dùng Nano Banana 2 Lite (không giữ được nhân vật).
- Đính kèm ảnh tham chiếu đúng thứ tự ghi ở mỗi mục, dán nguyên văn prompt, tải ảnh bản đầy đủ (2K) và lưu đúng tên.
- Phần tiếng Việt chỉ để bạn đọc: không dán vào prompt.


## 1. sheet_maker (model_sheet) · TẠO TAY
- Đính kèm: không
- Tạo tay: Google Flow (labs.google/fx/tools/flow), chọn ảnh (Image), model Nano Banana Pro, tỉ lệ 16:9, 2-4 bản; thêm ảnh tham chiếu theo đúng thứ tự (Add to prompt / ingredients); dán prompt; tải bản lớn nhất; kiểm watermark; kéo ảnh vào dashboard (nút Tải ảnh lên).
- Lưu thành: `refs/sheet_maker.png` (cần duyệt trước khi dùng làm tham chiếu)

```
Create one character model sheet image for the character "MAKER": a single 16:9 landscape image on a flat pure white background with no scenery, no ground line, no borders, no frames and no shadows.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.

CHARACTER "MAKER": an Ice Age clothing maker. Knee-length sleeveless tunic of rough grey-brown hide with a ragged hem, a lighter tan hide apron, a twisted leather cord belt tied at the front, a small leather pouch on the character's own right hip, dark hide leg wraps and soft rounded hide shoes; a bone tool tucked into the belt.

LAYOUT, three rows, every figure complete, same scale, evenly spaced, never overlapping:
Row 1, six full-body views of MAKER: front view, left side view, right side view, back view, three-quarter front view, three-quarter back view. In side views the face is a single dot eye near the facing edge and a short mouth stroke; in the back view the head is a blank white circle.
Row 2, 4 full-body action poses of MAKER: sitting cross-legged on the ground, sewing two pieces of hide together with a bone needle; pushing a large hide onto a wooden frame of lashed branches, one leg forward; holding up a piece of hide at arm's length and examining it closely; walking with a bundle of folded hides in both arms.
Row 3, 12 head-only expression circles of MAKER: neutral (two dot eyes and a short flat line mouth, no eyebrows); smiling (two dot eyes and a gently upturned line mouth, no eyebrows); happy (eyes as two small upward arcs and a wide open smile); angry (two short eyebrow strokes slanting down toward the centre and a downturned mouth); sad (eyebrow strokes with raised inner ends, a downturned mouth and one small tear); worried (wavy eyebrow strokes with raised inner ends and a small wavy mouth); scared (small high arched eyebrows, dot eyes and a small open oval mouth); surprised (high round eyebrows, dot eyes and a small round O mouth); confused (one eyebrow low and flat, the other high and arched, and a wavy mouth); determined (flat eyebrow bars pressed onto the eyes and a straight firm mouth); tired (half-closed heavy-lidded eyes and a small flat mouth); laughing (eyes closed as two upward arcs and a big open grin).
TEXT: a title in the top-left corner reading "MAKER" in bold condensed capitals, and a short label in plain dark grey sans-serif centred under each figure. No other text.
```

## 2. cast_sheet (cast_sheet) · TẠO TAY
- Đính kèm: 1) refs/sheet_maker.png
- Tạo tay: Google Flow (labs.google/fx/tools/flow), chọn ảnh (Image), model Nano Banana Pro, tỉ lệ 16:9, 2-4 bản; thêm ảnh tham chiếu theo đúng thứ tự (Add to prompt / ingredients); dán prompt; tải bản lớn nhất; kiểm watermark; kéo ảnh vào dashboard (nút Tải ảnh lên).
- Lưu thành: `refs/cast_sheet.png` (cần duyệt trước khi dùng làm tham chiếu)

```
Create one cast and pose reference sheet image for the video "Ancient demo": a single 16:9 landscape image on a flat pure white background with no scenery, no ground line, no borders, no frames and no shadows.

REFERENCES: Image 1 is the approved model sheet of MAKER. Draw each of these characters exactly as on its model sheet: same head, face, outline weight, clothing, colours, accessories and proportions. Do not copy the model sheets' layout or titles.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.
ANIMALS: animals use the same bold black outlines, flat muted fills and small solid black dot eyes as the people, with simple rounded shapes and realistic body proportions and size; fur appears only as a few short tick marks; animals never get stick limbs or white circle heads.

CAST, labelled with these exact names:
- "MAKER": an Ice Age clothing maker. Knee-length sleeveless tunic of rough grey-brown hide with a ragged hem, a lighter tan hide apron, a twisted leather cord belt tied at the front, a small leather pouch on the character's own right hip, dark hide leg wraps and soft rounded hide shoes; a bone tool tucked into the belt.
- "HUNTER": an Ice Age hunter, the same height as MAKER. Long dark brown fur cape over a hide tunic, a bead necklace of small shells, hide leg wraps, soft hide boots; carries a long wooden spear in the character's own right hand.
- "WOLF": a grey wolf, shoulder height about half of MAKER's height, thick grey fur shown with a few tick marks, pale belly, bushy tail.

LAYOUT: 2 rows of full-body figures, then one row of expression heads. Every figure complete, evenly spaced, never overlapping; each character always drawn at the same scale as its front view; the feet of each row on one shared invisible baseline.
Row 1: MAKER group (print "MAKER" once above it): MAKER front view, standing relaxed; MAKER sitting cross-legged on the ground, sewing two pieces of hide together with a bone needle; MAKER pushing a large hide onto a wooden frame of lashed branches, one leg forward; MAKER holding up a piece of hide at arm's length and examining it closely; HUNTER group (print "HUNTER" once above it): HUNTER front view, standing relaxed; HUNTER walking with the spear held upright; WOLF group (print "WOLF" once above it): WOLF front view, standing relaxed;
Row 2: WOLF group, continued (no name above it): WOLF sitting calmly on its haunches;
Row 3, head-only expression circles (the same head for every character): determined: flat eyebrow bars pressed onto the eyes and a straight firm mouth (label "determined"); neutral: two dot eyes and a short flat line mouth, no eyebrows (label "neutral"); smiling: two dot eyes and a gently upturned line mouth, no eyebrows (label "smiling"); happy: eyes as two small upward arcs and a wide open smile (label "happy").
TEXT: a title in the top-left corner reading "ANCIENT DEMO: CAST AND POSES" in bold condensed capitals; each character name printed once above its group in bold capitals; one-word labels under the expression heads in plain dark grey sans-serif; no other text and no labels under the full-body figures.
```

## 3. 01-01 (scene) · TẠO TAY
- Đính kèm: 1) refs/cast_sheet.png
- Tạo tay: Google Flow (labs.google/fx/tools/flow), chọn ảnh (Image), model Nano Banana Pro, tỉ lệ 16:9, 2-4 bản; thêm ảnh tham chiếu theo đúng thứ tự (Add to prompt / ingredients); dán prompt; tải bản lớn nhất; kiểm watermark; kéo ảnh vào dashboard (nút Tải ảnh lên).
- Lưu thành: `frames/001_01-01.png`

```
REFERENCES: Image 1 is the approved cast and pose sheet for this video: use it only for each character's identity (head, face, outline weight, clothing, colours, accessories and proportions). Do not copy the reference sheet's white background, layout, labels or poses; draw a new scene.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.

SCENE: MAKER sits near the fire sewing a hide garment.
CHARACTERS:
- MAKER, exactly as labelled "MAKER" on the cast sheet (an Ice Age clothing maker. Knee-length sleeveless tunic of rough grey-brown hide with a ragged hem, a lighter tan hide apron, a twisted leather cord belt tied at the front, a small leather pouch on the character's own right hip, dark hide leg wraps and soft rounded hide shoes; a bone tool tucked into the belt.): sitting cross-legged on the ground, sewing two pieces of hide together with a bone needle; expression: flat eyebrow bars pressed onto the eyes and a straight firm mouth; facing the viewer.
SETTING: the wide mouth of a limestone cave in winter, snow outside, a small fire inside on stone. SETTING STYLE: the environment is drawn in the same flat cartoon style but quieter: slightly thinner outlines, lower contrast, muted desaturated colours, simple shapes and a few texture marks, with clear depth from foreground to background. Keep a mid-tone surface behind every white head so the heads stay readable.
Make every garment, tool, object and building historically accurate for the Upper Palaeolithic in Ice Age Europe; nothing anachronistic.
CAMERA: medium wide shot.
FORMAT: one single widescreen 16:9 landscape image. Keep every character and key object well inside the frame, away from the edges and away from the bottom-right corner.
The image contains no text at all: no letters, numbers, labels, captions, logos or speech bubbles; every paper, screen and sign is blank.
```

## 4. 01-02 (scene) · tự động (agy)
- Đính kèm: 1) refs/cast_sheet.png
- Runner tools/gemini/agy_images.py tạo tự động; tạo tay cũng được rồi tải lên.
- Lưu thành: `frames/002_01-02.png`

```
REFERENCES: Image 1 is the approved cast and pose sheet for this video: use it only for each character's identity (head, face, outline weight, clothing, colours, accessories and proportions). Do not copy the reference sheet's white background, layout, labels or poses; draw a new scene.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.

SCENE: MAKER stretches a hide on the drying frame while HUNTER walks into camp.
CHARACTERS:
- MAKER, exactly as labelled "MAKER" on the cast sheet (an Ice Age clothing maker. Knee-length sleeveless tunic of rough grey-brown hide with a ragged hem, a lighter tan hide apron, a twisted leather cord belt tied at the front, a small leather pouch on the character's own right hip, dark hide leg wraps and soft rounded hide shoes; a bone tool tucked into the belt.): pushing a large hide onto a wooden frame of lashed branches, one leg forward; expression: two dot eyes and a short flat line mouth, no eyebrows; facing right.
- HUNTER, exactly as labelled "HUNTER" on the cast sheet (an Ice Age hunter, the same height as MAKER. Long dark brown fur cape over a hide tunic, a bead necklace of small shells, hide leg wraps, soft hide boots; carries a long wooden spear in the character's own right hand.): walking with the spear held upright; expression: two dot eyes and a gently upturned line mouth, no eyebrows; facing left.
SETTING: an open camp on a cold grassy steppe, a hide-covered shelter, a drying rack, distant hills. SETTING STYLE: the environment is drawn in the same flat cartoon style but quieter: slightly thinner outlines, lower contrast, muted desaturated colours, simple shapes and a few texture marks, with clear depth from foreground to background. Keep a mid-tone surface behind every white head so the heads stay readable.
Make every garment, tool, object and building historically accurate for the Upper Palaeolithic in Ice Age Europe; nothing anachronistic.
CAMERA: wide shot.
FORMAT: one single widescreen 16:9 landscape image. Keep every character and key object well inside the frame, away from the edges and away from the bottom-right corner.
The image contains no text at all: no letters, numbers, labels, captions, logos or speech bubbles; every paper, screen and sign is blank.
```

## 5. 01-03 (scene) · tự động (agy)
- Đính kèm: 1) refs/cast_sheet.png, 2) frames/002_01-02.png
- Runner tools/gemini/agy_images.py tạo tự động; tạo tay cũng được rồi tải lên.
- Lưu thành: `frames/003_01-03.png`

```
REFERENCES: Image 1 is the approved cast and pose sheet for this video: use it only for each character's identity (head, face, outline weight, clothing, colours, accessories and proportions). Image 2 is the previous scene: keep its location, background, palette and lighting. Do not copy the reference sheet's white background, layout, labels or poses; draw a new scene.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.
ANIMALS: animals use the same bold black outlines, flat muted fills and small solid black dot eyes as the people, with simple rounded shapes and realistic body proportions and size; fur appears only as a few short tick marks; animals never get stick limbs or white circle heads.

SCENE: A wolf watches from the edge of the camp as MAKER inspects the finished hide.
CHARACTERS:
- MAKER, exactly as labelled "MAKER" on the cast sheet (an Ice Age clothing maker. Knee-length sleeveless tunic of rough grey-brown hide with a ragged hem, a lighter tan hide apron, a twisted leather cord belt tied at the front, a small leather pouch on the character's own right hip, dark hide leg wraps and soft rounded hide shoes; a bone tool tucked into the belt.): holding up a piece of hide at arm's length and examining it closely; expression: eyes as two small upward arcs and a wide open smile; facing right.
- WOLF, exactly as labelled "WOLF" on the cast sheet (a grey wolf, shoulder height about half of MAKER's height, thick grey fur shown with a few tick marks, pale belly, bushy tail.): sitting calmly on its haunches; expression: two dot eyes and a short flat line mouth, no eyebrows; facing left.
SETTING: an open camp on a cold grassy steppe, a hide-covered shelter, a drying rack, distant hills. SETTING STYLE: the environment is drawn in the same flat cartoon style but quieter: slightly thinner outlines, lower contrast, muted desaturated colours, simple shapes and a few texture marks, with clear depth from foreground to background. Keep a mid-tone surface behind every white head so the heads stay readable.
Make every garment, tool, object and building historically accurate for the Upper Palaeolithic in Ice Age Europe; nothing anachronistic.
CAMERA: wide shot.
FORMAT: one single widescreen 16:9 landscape image. Keep every character and key object well inside the frame, away from the edges and away from the bottom-right corner.
The image contains no text at all: no letters, numbers, labels, captions, logos or speech bubbles; every paper, screen and sign is blank.
```
