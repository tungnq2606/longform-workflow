# Prompt pack: Rent vs pay

Style: stickman-v1. Tạo ảnh theo đúng thứ tự dưới đây. Các bảng nhân vật (model sheet, cast sheet) phải được duyệt trước khi tạo cảnh.

Cách làm tay (khi không chạy tự động bằng Gemini CLI):
- Google Flow: chọn Image, model Nano Banana Pro (hoặc 2.1), tỉ lệ 16:9. Không dùng Nano Banana 2 Lite (không giữ được nhân vật).
- Đính kèm ảnh tham chiếu đúng thứ tự ghi ở mỗi mục, dán nguyên văn prompt, tải ảnh bản đầy đủ (2K) và lưu đúng tên.
- Phần tiếng Việt chỉ để bạn đọc: không dán vào prompt.


## 1. sheet_worker (model_sheet) · TẠO TAY
- Đính kèm: không
- Tạo tay: Google Flow (labs.google/fx/tools/flow), chọn ảnh (Image), model Nano Banana Pro, tỉ lệ 16:9, 2-4 bản; thêm ảnh tham chiếu theo đúng thứ tự (Add to prompt / ingredients); dán prompt; tải bản lớn nhất; kiểm watermark; kéo ảnh vào dashboard (nút Tải ảnh lên).
- Lưu thành: `refs/sheet_worker.png` (cần duyệt trước khi dùng làm tham chiếu)

```
Create one character model sheet image for the character "WORKER": a single 16:9 landscape image on a flat pure white background with no scenery, no ground line, no borders, no frames and no shadows.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.

CHARACTER "WORKER": a young American full-time worker. Faded dusty-blue button-up work shirt with sleeves rolled to the elbow, worn untucked; khaki chino trousers; plain brown belt; grey sneakers; a navy canvas messenger bag on the character's own right hip, strap across the chest; a lanyard with a blank white ID card. No logos and no writing on any clothing.

LAYOUT, three rows, every figure complete, same scale, evenly spaced, never overlapping:
Row 1, six full-body views of WORKER: front view, left side view, right side view, back view, three-quarter front view, three-quarter back view. In side views the face is a single dot eye near the facing edge and a short mouth stroke; in the back view the head is a blank white circle.
Row 2, 6 full-body action poses of WORKER: waving hello with one arm raised high; holding up a sheet of paper in front of the chest with both hands; pointing to the right with one arm held straight out; shrugging with both forearms raised and the palms up; thinking with one hand on the chin and the other arm hanging; running fast, leaning forward, the legs as stick lines in a long stride.
Row 3, 12 head-only expression circles of WORKER: neutral (two dot eyes and a short flat line mouth, no eyebrows); smiling (two dot eyes and a gently upturned line mouth, no eyebrows); happy (eyes as two small upward arcs and a wide open smile); angry (two short eyebrow strokes slanting down toward the centre and a downturned mouth); sad (eyebrow strokes with raised inner ends, a downturned mouth and one small tear); worried (wavy eyebrow strokes with raised inner ends and a small wavy mouth); scared (small high arched eyebrows, dot eyes and a small open oval mouth); surprised (high round eyebrows, dot eyes and a small round O mouth); confused (one eyebrow low and flat, the other high and arched, and a wavy mouth); determined (flat eyebrow bars pressed onto the eyes and a straight firm mouth); tired (half-closed heavy-lidded eyes and a small flat mouth); laughing (eyes closed as two upward arcs and a big open grin).
TEXT: a title in the top-left corner reading "WORKER" in bold condensed capitals, and a short label in plain dark grey sans-serif centred under each figure. No other text.
```

## 2. cast_sheet (cast_sheet) · TẠO TAY
- Đính kèm: 1) refs/sheet_worker.png
- Tạo tay: Google Flow (labs.google/fx/tools/flow), chọn ảnh (Image), model Nano Banana Pro, tỉ lệ 16:9, 2-4 bản; thêm ảnh tham chiếu theo đúng thứ tự (Add to prompt / ingredients); dán prompt; tải bản lớn nhất; kiểm watermark; kéo ảnh vào dashboard (nút Tải ảnh lên).
- Lưu thành: `refs/cast_sheet.png` (cần duyệt trước khi dùng làm tham chiếu)

```
Create one cast and pose reference sheet image for the video "Rent vs pay": a single 16:9 landscape image on a flat pure white background with no scenery, no ground line, no borders, no frames and no shadows.

REFERENCES: Image 1 is the approved model sheet of WORKER. Draw each of these characters exactly as on its model sheet: same head, face, outline weight, clothing, colours, accessories and proportions. Do not copy the model sheets' layout or titles.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.

CAST, labelled with these exact names:
- "WORKER": a young American full-time worker. Faded dusty-blue button-up work shirt with sleeves rolled to the elbow, worn untucked; khaki chino trousers; plain brown belt; grey sneakers; a navy canvas messenger bag on the character's own right hip, strap across the chest; a lanyard with a blank white ID card. No logos and no writing on any clothing.
- "PAY": a runner who stands for pay, the same height as WORKER. Muted sage-green zip tracksuit jacket and matching trousers, white sneakers, a white sweatband on the character's own left wrist; carries a rolled-up paycheck like a relay baton in the character's own right hand. No writing on clothing.
- "RENT": a runner who stands for rent, the same height as WORKER. Muted burnt-orange tracksuit jacket, dark grey trousers, orange sneakers, a small brick-red backpack shaped like a little house on the back. No writing on clothing.

LAYOUT: 2 rows of full-body figures, then one row of expression heads. Every figure complete, evenly spaced, never overlapping; each character always drawn at the same scale as its front view; the feet of each row on one shared invisible baseline.
Row 1: WORKER group (print "WORKER" once above it): WORKER front view, standing relaxed; WORKER standing, one arm stretched out to the side with the palm up, presenting the empty space next to them; WORKER balancing on a tightrope with both arms stretched out sideways and the knees slightly bent; WORKER thinking with one hand on the chin and the other arm hanging; WORKER waving hello with one arm raised high; WORKER holding up a sheet of paper in front of the chest with both hands; WORKER shrugging with both forearms raised and the palms up;
Row 2: WORKER group, continued (no name above it): WORKER pointing to the right with one arm held straight out; PAY group (print "PAY" once above it): PAY front view, standing relaxed; PAY running but tired, leaning back a little with heavy steps; PAY running fast, leaning forward, the legs as stick lines in a long stride; RENT group (print "RENT" once above it): RENT front view, standing relaxed; RENT running fast, leaning forward, the legs as stick lines in a long stride;
Row 3, head-only expression circles (the same head for every character): neutral: two dot eyes and a short flat line mouth, no eyebrows (label "neutral"); worried: wavy eyebrow strokes with raised inner ends and a small wavy mouth (label "worried"); smiling: two dot eyes and a gently upturned line mouth, no eyebrows (label "smiling"); tired: half-closed heavy-lidded eyes and a small flat mouth (label "tired"); determined: flat eyebrow bars pressed onto the eyes and a straight firm mouth (label "determined"); surprised: high round eyebrows, dot eyes and a small round O mouth (label "surprised"); confused: one eyebrow low and flat, the other high and arched, and a wavy mouth (label "confused"); happy: eyes as two small upward arcs and a wide open smile (label "happy").
TEXT: a title in the top-left corner reading "RENT VS PAY: CAST AND POSES" in bold condensed capitals; each character name printed once above its group in bold capitals; one-word labels under the expression heads in plain dark grey sans-serif; no other text and no labels under the full-body figures.
```

## 3. 01-01 (scene) · TẠO TAY
- Đính kèm: 1) refs/cast_sheet.png
- Tạo tay: Google Flow (labs.google/fx/tools/flow), chọn ảnh (Image), model Nano Banana Pro, tỉ lệ 16:9, 2-4 bản; thêm ảnh tham chiếu theo đúng thứ tự (Add to prompt / ingredients); dán prompt; tải bản lớn nhất; kiểm watermark; kéo ảnh vào dashboard (nút Tải ảnh lên).
- Lưu thành: `frames/001_01-01.png`

```
REFERENCES: Image 1 is the approved cast and pose sheet for this video: use it only for each character's identity (head, face, outline weight, clothing, colours, accessories and proportions). Do not copy the reference sheet's white background, layout, labels or poses; draw a new scene.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.

SCENE: WORKER stands on the left and presents the empty right side of the room to the viewer.
CHARACTERS:
- WORKER, exactly as labelled "WORKER" on the cast sheet (a young American full-time worker. Faded dusty-blue button-up work shirt with sleeves rolled to the elbow, worn untucked; khaki chino trousers; plain brown belt; grey sneakers; a navy canvas messenger bag on the character's own right hip, strap across the chest; a lanyard with a blank white ID card. No logos and no writing on any clothing.): standing, one arm stretched out to the side with the palm up, presenting the empty space next to them; expression: two dot eyes and a short flat line mouth, no eyebrows; facing the viewer, body turned slightly right.
SETTING: a tidy, modest apartment living room in a US city: a small sofa, a window with city buildings outside, a floor lamp and a rug. SETTING STYLE: the environment is drawn in the same flat cartoon style but quieter: slightly thinner outlines, lower contrast, muted desaturated colours, simple shapes and a few texture marks, with clear depth from foreground to background. Keep a mid-tone surface behind every white head so the heads stay readable.
COMPOSITION: keep the right half of the frame calm and uncluttered (plain wall, sky or ground) for graphics that are added later.
CAMERA: medium wide shot at eye level.
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

SCENE: WORKER balances in the middle of the tightrope, looking down nervously.
CHARACTERS:
- WORKER, exactly as labelled "WORKER" on the cast sheet (a young American full-time worker. Faded dusty-blue button-up work shirt with sleeves rolled to the elbow, worn untucked; khaki chino trousers; plain brown belt; grey sneakers; a navy canvas messenger bag on the character's own right hip, strap across the chest; a lanyard with a blank white ID card. No logos and no writing on any clothing.): balancing on a tightrope with both arms stretched out sideways and the knees slightly bent; expression: wavy eyebrow strokes with raised inner ends and a small wavy mouth; facing the viewer.
SETTING: a tightrope stretched between two tall wooden poles high above a city street at sunset, buildings far below. SETTING STYLE: the environment is drawn in the same flat cartoon style but quieter: slightly thinner outlines, lower contrast, muted desaturated colours, simple shapes and a few texture marks, with clear depth from foreground to background. Keep a mid-tone surface behind every white head so the heads stay readable.
CAMERA: wide shot from slightly below.
FORMAT: one single widescreen 16:9 landscape image. Keep every character and key object well inside the frame, away from the edges and away from the bottom-right corner.
The image contains no text at all: no letters, numbers, labels, captions, logos or speech bubbles; every paper, screen and sign is blank.
```

## 5. 01-03 (scene) · tự động (agy)
- Đính kèm: 1) refs/cast_sheet.png
- Runner tools/gemini/agy_images.py tạo tự động; tạo tay cũng được rồi tải lên.
- Lưu thành: `frames/003_01-03.png`

```
REFERENCES: Image 1 is the approved cast and pose sheet for this video: use it only for each character's identity (head, face, outline weight, clothing, colours, accessories and proportions). Do not copy the reference sheet's white background, layout, labels or poses; draw a new scene.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.

SCENE: RENT runs ahead on the right side of the track, confident; PAY runs behind on the left, struggling.
CHARACTERS:
- RENT, exactly as labelled "RENT" on the cast sheet (a runner who stands for rent, the same height as WORKER. Muted burnt-orange tracksuit jacket, dark grey trousers, orange sneakers, a small brick-red backpack shaped like a little house on the back. No writing on clothing.): running fast, leaning forward, the legs as stick lines in a long stride; expression: two dot eyes and a gently upturned line mouth, no eyebrows; facing right.
- PAY, exactly as labelled "PAY" on the cast sheet (a runner who stands for pay, the same height as WORKER. Muted sage-green zip tracksuit jacket and matching trousers, white sneakers, a white sweatband on the character's own left wrist; carries a rolled-up paycheck like a relay baton in the character's own right hand. No writing on clothing.): running but tired, leaning back a little with heavy steps; expression: half-closed heavy-lidded eyes and a small flat mouth; facing right.
SETTING: an outdoor running track at dusk, white lane lines, simple stadium stands far behind, a finish line on the right. SETTING STYLE: the environment is drawn in the same flat cartoon style but quieter: slightly thinner outlines, lower contrast, muted desaturated colours, simple shapes and a few texture marks, with clear depth from foreground to background. Keep a mid-tone surface behind every white head so the heads stay readable.
CAMERA: wide side view of the track.
FORMAT: one single widescreen 16:9 landscape image. Keep every character and key object well inside the frame, away from the edges and away from the bottom-right corner.
The image contains no text at all: no letters, numbers, labels, captions, logos or speech bubbles; every paper, screen and sign is blank.
```

## 6. 01-04 (scene) · tự động (agy)
- Đính kèm: 1) refs/cast_sheet.png, 2) frames/003_01-03.png
- Runner tools/gemini/agy_images.py tạo tự động; tạo tay cũng được rồi tải lên.
- Lưu thành: `frames/004_01-04.png`

```
REFERENCES: Image 1 is the approved cast and pose sheet for this video: use it only for each character's identity (head, face, outline weight, clothing, colours, accessories and proportions). Image 2 is the previous scene: keep its location, background, palette and lighting. Do not copy the reference sheet's white background, layout, labels or poses; draw a new scene.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.

SCENE: PAY passes RENT just before the finish line on the right; RENT looks surprised.
CHARACTERS:
- PAY, exactly as labelled "PAY" on the cast sheet (a runner who stands for pay, the same height as WORKER. Muted sage-green zip tracksuit jacket and matching trousers, white sneakers, a white sweatband on the character's own left wrist; carries a rolled-up paycheck like a relay baton in the character's own right hand. No writing on clothing.): running fast, leaning forward, the legs as stick lines in a long stride; expression: flat eyebrow bars pressed onto the eyes and a straight firm mouth; facing right.
- RENT, exactly as labelled "RENT" on the cast sheet (a runner who stands for rent, the same height as WORKER. Muted burnt-orange tracksuit jacket, dark grey trousers, orange sneakers, a small brick-red backpack shaped like a little house on the back. No writing on clothing.): running fast, leaning forward, the legs as stick lines in a long stride; expression: high round eyebrows, dot eyes and a small round O mouth; facing right.
SETTING: an outdoor running track at dusk, white lane lines, simple stadium stands far behind, a finish line on the right. SETTING STYLE: the environment is drawn in the same flat cartoon style but quieter: slightly thinner outlines, lower contrast, muted desaturated colours, simple shapes and a few texture marks, with clear depth from foreground to background. Keep a mid-tone surface behind every white head so the heads stay readable.
CAMERA: wide side view of the track.
FORMAT: one single widescreen 16:9 landscape image. Keep every character and key object well inside the frame, away from the edges and away from the bottom-right corner.
The image contains no text at all: no letters, numbers, labels, captions, logos or speech bubbles; every paper, screen and sign is blank.
```

## 7. 01-05 (scene) · tự động (agy)
- Đính kèm: 1) refs/cast_sheet.png, 2) frames/004_01-04.png
- Runner tools/gemini/agy_images.py tạo tự động; tạo tay cũng được rồi tải lên.
- Lưu thành: `frames/005_01-05.png`

```
REFERENCES: Image 1 is the approved cast and pose sheet for this video: use it only for each character's identity (head, face, outline weight, clothing, colours, accessories and proportions). Image 2 is the previous scene: keep its location, background, palette and lighting. Do not copy the reference sheet's white background, layout, labels or poses; draw a new scene.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.

SCENE: The empty track; WORKER stands at the edge and studies one middle stretch of the track.
CHARACTERS:
- WORKER, exactly as labelled "WORKER" on the cast sheet (a young American full-time worker. Faded dusty-blue button-up work shirt with sleeves rolled to the elbow, worn untucked; khaki chino trousers; plain brown belt; grey sneakers; a navy canvas messenger bag on the character's own right hip, strap across the chest; a lanyard with a blank white ID card. No logos and no writing on any clothing.): thinking with one hand on the chin and the other arm hanging; expression: one eyebrow low and flat, the other high and arched, and a wavy mouth; facing right.
SETTING: an outdoor running track at dusk, white lane lines, simple stadium stands far behind, a finish line on the right. SETTING STYLE: the environment is drawn in the same flat cartoon style but quieter: slightly thinner outlines, lower contrast, muted desaturated colours, simple shapes and a few texture marks, with clear depth from foreground to background. Keep a mid-tone surface behind every white head so the heads stay readable.
COMPOSITION: keep the upper middle of the frame calm and uncluttered (plain wall, sky or ground) for graphics that are added later.
CAMERA: wide shot.
FORMAT: one single widescreen 16:9 landscape image. Keep every character and key object well inside the frame, away from the edges and away from the bottom-right corner.
The image contains no text at all: no letters, numbers, labels, captions, logos or speech bubbles; every paper, screen and sign is blank.
```

## 8. 01-06 (scene) · tự động (agy)
- Đính kèm: 1) refs/cast_sheet.png
- Runner tools/gemini/agy_images.py tạo tự động; tạo tay cũng được rồi tải lên.
- Lưu thành: `frames/006_01-06.png`

```
REFERENCES: Image 1 is the approved cast and pose sheet for this video: use it only for each character's identity (head, face, outline weight, clothing, colours, accessories and proportions). Do not copy the reference sheet's white background, layout, labels or poses; draw a new scene.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.

SCENE: WORKER waves at the viewer in front of a small apartment building, a compact car parked nearby.
CHARACTERS:
- WORKER, exactly as labelled "WORKER" on the cast sheet (a young American full-time worker. Faded dusty-blue button-up work shirt with sleeves rolled to the elbow, worn untucked; khaki chino trousers; plain brown belt; grey sneakers; a navy canvas messenger bag on the character's own right hip, strap across the chest; a lanyard with a blank white ID card. No logos and no writing on any clothing.): waving hello with one arm raised high; expression: eyes as two small upward arcs and a wide open smile; facing the viewer.
SETTING: a quiet US neighbourhood street with small apartment buildings, a parked compact car and a sidewalk with trees. SETTING STYLE: the environment is drawn in the same flat cartoon style but quieter: slightly thinner outlines, lower contrast, muted desaturated colours, simple shapes and a few texture marks, with clear depth from foreground to background. Keep a mid-tone surface behind every white head so the heads stay readable.
CAMERA: medium wide shot at eye level.
FORMAT: one single widescreen 16:9 landscape image. Keep every character and key object well inside the frame, away from the edges and away from the bottom-right corner.
The image contains no text at all: no letters, numbers, labels, captions, logos or speech bubbles; every paper, screen and sign is blank.
```

## 9. 01-07 (scene) · tự động (agy)
- Đính kèm: 1) refs/cast_sheet.png
- Runner tools/gemini/agy_images.py tạo tự động; tạo tay cũng được rồi tải lên.
- Lưu thành: `frames/007_01-07.png`

```
REFERENCES: Image 1 is the approved cast and pose sheet for this video: use it only for each character's identity (head, face, outline weight, clothing, colours, accessories and proportions). Do not copy the reference sheet's white background, layout, labels or poses; draw a new scene.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.

SCENE: WORKER proudly holds up a blank paycheck on the left of the frame.
CHARACTERS:
- WORKER, exactly as labelled "WORKER" on the cast sheet (a young American full-time worker. Faded dusty-blue button-up work shirt with sleeves rolled to the elbow, worn untucked; khaki chino trousers; plain brown belt; grey sneakers; a navy canvas messenger bag on the character's own right hip, strap across the chest; a lanyard with a blank white ID card. No logos and no writing on any clothing.): holding up a sheet of paper in front of the chest with both hands; expression: two dot eyes and a gently upturned line mouth, no eyebrows; facing the viewer.
SETTING: a tidy, modest apartment living room in a US city: a small sofa, a window with city buildings outside, a floor lamp and a rug. SETTING STYLE: the environment is drawn in the same flat cartoon style but quieter: slightly thinner outlines, lower contrast, muted desaturated colours, simple shapes and a few texture marks, with clear depth from foreground to background. Keep a mid-tone surface behind every white head so the heads stay readable.
COMPOSITION: keep the right half of the frame calm and uncluttered (plain wall, sky or ground) for graphics that are added later.
CAMERA: medium shot.
FORMAT: one single widescreen 16:9 landscape image. Keep every character and key object well inside the frame, away from the edges and away from the bottom-right corner.
The image contains no text at all: no letters, numbers, labels, captions, logos or speech bubbles; every paper, screen and sign is blank.
```

## 10. 01-08 (scene) · tự động (agy)
- Đính kèm: 1) refs/cast_sheet.png, 2) frames/007_01-07.png
- Runner tools/gemini/agy_images.py tạo tự động; tạo tay cũng được rồi tải lên.
- Lưu thành: `frames/008_01-08.png`

```
REFERENCES: Image 1 is the approved cast and pose sheet for this video: use it only for each character's identity (head, face, outline weight, clothing, colours, accessories and proportions). Image 2 is the previous scene: keep its location, background, palette and lighting. Do not copy the reference sheet's white background, layout, labels or poses; draw a new scene.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.

SCENE: WORKER presents the empty right side of the room, looking a little worried.
CHARACTERS:
- WORKER, exactly as labelled "WORKER" on the cast sheet (a young American full-time worker. Faded dusty-blue button-up work shirt with sleeves rolled to the elbow, worn untucked; khaki chino trousers; plain brown belt; grey sneakers; a navy canvas messenger bag on the character's own right hip, strap across the chest; a lanyard with a blank white ID card. No logos and no writing on any clothing.): standing, one arm stretched out to the side with the palm up, presenting the empty space next to them; expression: wavy eyebrow strokes with raised inner ends and a small wavy mouth; facing the viewer, body turned slightly right.
SETTING: a tidy, modest apartment living room in a US city: a small sofa, a window with city buildings outside, a floor lamp and a rug. SETTING STYLE: the environment is drawn in the same flat cartoon style but quieter: slightly thinner outlines, lower contrast, muted desaturated colours, simple shapes and a few texture marks, with clear depth from foreground to background. Keep a mid-tone surface behind every white head so the heads stay readable.
COMPOSITION: keep the right half of the frame calm and uncluttered (plain wall, sky or ground) for graphics that are added later.
CAMERA: medium wide shot at eye level.
FORMAT: one single widescreen 16:9 landscape image. Keep every character and key object well inside the frame, away from the edges and away from the bottom-right corner.
The image contains no text at all: no letters, numbers, labels, captions, logos or speech bubbles; every paper, screen and sign is blank.
```

## 11. 01-09 (scene) · tự động (agy)
- Đính kèm: 1) refs/cast_sheet.png
- Runner tools/gemini/agy_images.py tạo tự động; tạo tay cũng được rồi tải lên.
- Lưu thành: `frames/009_01-09.png`

```
REFERENCES: Image 1 is the approved cast and pose sheet for this video: use it only for each character's identity (head, face, outline weight, clothing, colours, accessories and proportions). Do not copy the reference sheet's white background, layout, labels or poses; draw a new scene.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.

SCENE: WORKER shrugs next to the kitchen table; two blank wall calendars hang behind, one on each side.
CHARACTERS:
- WORKER, exactly as labelled "WORKER" on the cast sheet (a young American full-time worker. Faded dusty-blue button-up work shirt with sleeves rolled to the elbow, worn untucked; khaki chino trousers; plain brown belt; grey sneakers; a navy canvas messenger bag on the character's own right hip, strap across the chest; a lanyard with a blank white ID card. No logos and no writing on any clothing.): shrugging with both forearms raised and the palms up; expression: two dot eyes and a short flat line mouth, no eyebrows; facing the viewer.
SETTING: a small apartment kitchen table with a laptop, a calculator, a stack of bills and a mug, a wall calendar behind. SETTING STYLE: the environment is drawn in the same flat cartoon style but quieter: slightly thinner outlines, lower contrast, muted desaturated colours, simple shapes and a few texture marks, with clear depth from foreground to background. Keep a mid-tone surface behind every white head so the heads stay readable.
CAMERA: medium wide shot.
FORMAT: one single widescreen 16:9 landscape image. Keep every character and key object well inside the frame, away from the edges and away from the bottom-right corner.
The image contains no text at all: no letters, numbers, labels, captions, logos or speech bubbles; every paper, screen and sign is blank.
```

## 12. 01-10 (scene) · tự động (agy)
- Đính kèm: 1) refs/cast_sheet.png
- Runner tools/gemini/agy_images.py tạo tự động; tạo tay cũng được rồi tải lên.
- Lưu thành: `frames/010_01-10.png`

```
REFERENCES: Image 1 is the approved cast and pose sheet for this video: use it only for each character's identity (head, face, outline weight, clothing, colours, accessories and proportions). Do not copy the reference sheet's white background, layout, labels or poses; draw a new scene.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.
BACKGROUND PEOPLE: any unnamed people are the same clothed stick figures in plain muted clothes, smaller and simpler, with no accessories that belong to a named character.

SCENE: One small neighbour stands in front of each of the eight houses.
BACKGROUND PEOPLE: eight small neighbours of different ages, one in front of each house; about half of them look worried, the others calm
SETTING: a row of eight small houses side by side along a residential street, some porch lights on. SETTING STYLE: the environment is drawn in the same flat cartoon style but quieter: slightly thinner outlines, lower contrast, muted desaturated colours, simple shapes and a few texture marks, with clear depth from foreground to background. Keep a mid-tone surface behind every white head so the heads stay readable.
CAMERA: wide shot of the whole row of houses.
FORMAT: one single widescreen 16:9 landscape image. Keep every character and key object well inside the frame, away from the edges and away from the bottom-right corner.
The image contains no text at all: no letters, numbers, labels, captions, logos or speech bubbles; every paper, screen and sign is blank.
```

## 13. 01-11 (scene) · tự động (agy)
- Đính kèm: 1) refs/cast_sheet.png
- Runner tools/gemini/agy_images.py tạo tự động; tạo tay cũng được rồi tải lên.
- Lưu thành: `frames/011_01-11.png`

```
REFERENCES: Image 1 is the approved cast and pose sheet for this video: use it only for each character's identity (head, face, outline weight, clothing, colours, accessories and proportions). Do not copy the reference sheet's white background, layout, labels or poses; draw a new scene.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.

SCENE: Close-up of WORKER raising one eyebrow at the viewer.
CHARACTERS:
- WORKER, exactly as labelled "WORKER" on the cast sheet (a young American full-time worker. Faded dusty-blue button-up work shirt with sleeves rolled to the elbow, worn untucked; khaki chino trousers; plain brown belt; grey sneakers; a navy canvas messenger bag on the character's own right hip, strap across the chest; a lanyard with a blank white ID card. No logos and no writing on any clothing.): thinking with one hand on the chin and the other arm hanging; expression: one eyebrow low and flat, the other high and arched, and a wavy mouth; facing the viewer.
SETTING: a quiet US neighbourhood street with small apartment buildings, a parked compact car and a sidewalk with trees. SETTING STYLE: the environment is drawn in the same flat cartoon style but quieter: slightly thinner outlines, lower contrast, muted desaturated colours, simple shapes and a few texture marks, with clear depth from foreground to background. Keep a mid-tone surface behind every white head so the heads stay readable.
COMPOSITION: keep the right half of the frame calm and uncluttered (plain wall, sky or ground) for graphics that are added later.
CAMERA: close-up of the head and shoulders on the left of the frame.
FORMAT: one single widescreen 16:9 landscape image. Keep every character and key object well inside the frame, away from the edges and away from the bottom-right corner.
The image contains no text at all: no letters, numbers, labels, captions, logos or speech bubbles; every paper, screen and sign is blank.
```

## 14. 01-12 (scene) · tự động (agy)
- Đính kèm: 1) refs/cast_sheet.png
- Runner tools/gemini/agy_images.py tạo tự động; tạo tay cũng được rồi tải lên.
- Lưu thành: `frames/012_01-12.png`

```
REFERENCES: Image 1 is the approved cast and pose sheet for this video: use it only for each character's identity (head, face, outline weight, clothing, colours, accessories and proportions). Do not copy the reference sheet's white background, layout, labels or poses; draw a new scene.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.

SCENE: WORKER sits at the kitchen table thinking, bills and a calculator in front of them.
CHARACTERS:
- WORKER, exactly as labelled "WORKER" on the cast sheet (a young American full-time worker. Faded dusty-blue button-up work shirt with sleeves rolled to the elbow, worn untucked; khaki chino trousers; plain brown belt; grey sneakers; a navy canvas messenger bag on the character's own right hip, strap across the chest; a lanyard with a blank white ID card. No logos and no writing on any clothing.): thinking with one hand on the chin and the other arm hanging; expression: two dot eyes and a short flat line mouth, no eyebrows; facing the viewer.
SETTING: a small apartment kitchen table with a laptop, a calculator, a stack of bills and a mug, a wall calendar behind. SETTING STYLE: the environment is drawn in the same flat cartoon style but quieter: slightly thinner outlines, lower contrast, muted desaturated colours, simple shapes and a few texture marks, with clear depth from foreground to background. Keep a mid-tone surface behind every white head so the heads stay readable.
CAMERA: medium shot.
FORMAT: one single widescreen 16:9 landscape image. Keep every character and key object well inside the frame, away from the edges and away from the bottom-right corner.
The image contains no text at all: no letters, numbers, labels, captions, logos or speech bubbles; every paper, screen and sign is blank.
```

## 15. 01-13 (scene) · tự động (agy)
- Đính kèm: 1) refs/cast_sheet.png
- Runner tools/gemini/agy_images.py tạo tự động; tạo tay cũng được rồi tải lên.
- Lưu thành: `frames/013_01-13.png`

```
REFERENCES: Image 1 is the approved cast and pose sheet for this video: use it only for each character's identity (head, face, outline weight, clothing, colours, accessories and proportions). Do not copy the reference sheet's white background, layout, labels or poses; draw a new scene.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.

SCENE: WORKER balances on the tightrope, steadier than before.
CHARACTERS:
- WORKER, exactly as labelled "WORKER" on the cast sheet (a young American full-time worker. Faded dusty-blue button-up work shirt with sleeves rolled to the elbow, worn untucked; khaki chino trousers; plain brown belt; grey sneakers; a navy canvas messenger bag on the character's own right hip, strap across the chest; a lanyard with a blank white ID card. No logos and no writing on any clothing.): balancing on a tightrope with both arms stretched out sideways and the knees slightly bent; expression: flat eyebrow bars pressed onto the eyes and a straight firm mouth; facing the viewer.
SETTING: a tightrope stretched between two tall wooden poles high above a city street at sunset, buildings far below. SETTING STYLE: the environment is drawn in the same flat cartoon style but quieter: slightly thinner outlines, lower contrast, muted desaturated colours, simple shapes and a few texture marks, with clear depth from foreground to background. Keep a mid-tone surface behind every white head so the heads stay readable.
CAMERA: wide shot from slightly below.
FORMAT: one single widescreen 16:9 landscape image. Keep every character and key object well inside the frame, away from the edges and away from the bottom-right corner.
The image contains no text at all: no letters, numbers, labels, captions, logos or speech bubbles; every paper, screen and sign is blank.
```

## 16. 01-14 (scene) · tự động (agy)
- Đính kèm: 1) refs/cast_sheet.png
- Runner tools/gemini/agy_images.py tạo tự động; tạo tay cũng được rồi tải lên.
- Lưu thành: `frames/014_01-14.png`

```
REFERENCES: Image 1 is the approved cast and pose sheet for this video: use it only for each character's identity (head, face, outline weight, clothing, colours, accessories and proportions). Do not copy the reference sheet's white background, layout, labels or poses; draw a new scene.

STYLE (stickman-v1): Flat 2D cartoon illustration. Every person is a clothed stick figure: a large, perfectly round, plain white head with a bold, even black outline, about one quarter of the figure's height. The face is only two small solid black vertical-oval dot eyes and one thin black line mouth, set slightly below the centre of the circle; the rest of the circle stays plain white. Short thick eyebrow strokes appear only when an expression needs them. The head sits directly on the collar with almost no neck. Arms are single thick solid black lines with crisp angular elbows, ending in small white oval mitten hands outlined in black. The body is a solid, believable, layered clothing silhouette about as wide as the head, on short legs with rounded soft shoes; standing legs are clothed trouser tubes, walking or running legs become single black stick lines that end in the same shoes. Figures are stocky, about 3.7 heads tall. Clothing and props use flat, muted, desaturated colour fills with bold black outlines, a few thin fold lines and sparse short texture tick marks. Flat colours only, with no gradients and no glossy highlights. Never add hair, a nose, ears, fingers, pupils, eye whites, skin colour, realistic anatomy, a 3D look or a photographic look.

SCENE: WORKER points toward a wooden signpost with three blank arrow signs on the right.
CHARACTERS:
- WORKER, exactly as labelled "WORKER" on the cast sheet (a young American full-time worker. Faded dusty-blue button-up work shirt with sleeves rolled to the elbow, worn untucked; khaki chino trousers; plain brown belt; grey sneakers; a navy canvas messenger bag on the character's own right hip, strap across the chest; a lanyard with a blank white ID card. No logos and no writing on any clothing.): pointing to the right with one arm held straight out; expression: flat eyebrow bars pressed onto the eyes and a straight firm mouth; facing right.
SETTING: a quiet US neighbourhood street with small apartment buildings, a parked compact car and a sidewalk with trees. SETTING STYLE: the environment is drawn in the same flat cartoon style but quieter: slightly thinner outlines, lower contrast, muted desaturated colours, simple shapes and a few texture marks, with clear depth from foreground to background. Keep a mid-tone surface behind every white head so the heads stay readable.
CAMERA: medium wide shot.
FORMAT: one single widescreen 16:9 landscape image. Keep every character and key object well inside the frame, away from the edges and away from the bottom-right corner.
The image contains no text at all: no letters, numbers, labels, captions, logos or speech bubbles; every paper, screen and sign is blank.
```
