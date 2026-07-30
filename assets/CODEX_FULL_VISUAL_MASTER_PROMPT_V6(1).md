# MASTER TASK FOR CODEX — FULL VISUAL UPGRADE V6

## Контекст проекта

Продолжай работу **в существующем репозитории Godot 4 + Python**. Проект уже умеет:

- анализировать музыку;
- строить beat grid и phrase grid;
- генерировать movement events;
- сохранять существующие JSON-контракты;
- загружать и воспроизводить фоновый MP4;
- строить дорожку;
- создавать QA и clean render;
- использовать frame-locked viewport render → FFmpeg fallback;
- валидировать hit time, safe zone, lead time и choreography semantics.

Не создавай проект заново. Не переписывай рабочие системы, если для визуальной задачи достаточно additive-слоя.

Текущий результат функционально работает, но визуально заметно слабее референса. Главные обнаруженные проблемы:

1. следы/footprints развернуты и местами перепутаны left/right;
2. step cues выглядят как простые плоские плитки, а не как качественные игровые команды;
3. текущий шар/сфера выглядит непонятно и выпадает из визуального языка;
4. вместо сферы нужен небольшой объёмный летящий cube target с изображением/пиктограммой внутри;
5. cube target должен эффектно разрушаться при hit;
6. большие боковые препятствия для ухода влево/вправо выглядят плоскими и слабыми;
7. side obstacles иногда исчезают в середине кадра вместо того, чтобы пролететь мимо камеры;
8. cue не всегда уверенно посажены на lane и дорогу;
9. дорожка, cue и MP4-фон всё ещё не полностью ощущаются единым пространством;
10. hit feedback, глубина и визуальная драматургия слабее референса.

Цель — добиться качества, близкого к референсу **по ясности, объёму, чувству движения, игровому отклику и сценической постановке**, но не копировать его художественные ассеты, брендинг, интерфейс или точные модели.

---

# 0. НЕИЗМЕНЯЕМЫЕ СИСТЕМЫ И ГРАНИЦЫ РАБОТЫ

## Запрещено без отдельной объективной необходимости

Не переписывай:

- Analyzer GUI;
- beat detection;
- phrase-grid generation;
- choreography semantics;
- старые JSON-схемы;
- MP4 loading/playback integration;
- существующую систему hit_time;
- текущий deterministic/frame-locked render fallback;
- performer safe-zone semantics;
- действующий validation pipeline.

Разрешены только обратно совместимые additive-поля и визуальные конфигурации.

## Главный принцип

Работай как **Visual Production Upgrade Layer**:

```text
existing event JSON
→ visual cue resolver
→ asset/variant selection
→ placement and lifecycle
→ materials and FX
→ QA verification
→ clean render
```

---

# 1. ОБЯЗАТЕЛЬНЫЙ АУДИТ ПЕРЕД ИЗМЕНЕНИЯМИ

Сначала найди и изучи:

- самый новый QA-ролик;
- самый новый clean-ролик;
- последние preview frames;
- текущие сцены дорожки и obstacle factory;
- current cue mapping;
- movement-to-cue resolver;
- material resources;
- shaders;
- pooling/despawn logic;
- camera position/FOV;
- lane coordinate calculations;
- reference video и reference frames, имеющиеся в репозитории.

При наличии нескольких роликов используй самый новый успешно созданный visual/QA render. Не оценивай только исходный код: обязательно извлеки кадры и просмотри реальный результат.

Создай:

```text
docs/VISUAL_GAP_AUDIT_V6.md
```

В аудите зафиксируй:

1. текущий renderer и camera coordinate system;
2. направление world-forward и направление движения cue;
3. реальные lane center coordinates;
4. ширину lane;
5. judgment plane/world position;
6. текущие anchor/pivot rules;
7. список всех cue archetypes;
8. какие cue являются procedural, а какие импортированными;
9. какие left/right cues перепутаны;
10. где footprints развернуты;
11. почему они развернуты: texture UV, node rotation, negative scale, import transform или mirror logic;
12. какие cue висят над дорогой или проваливаются;
13. какие cue слишком мелкие на instruction_time;
14. какие cue путаются между собой;
15. текущий sphere archetype и movement semantics, которые его используют;
16. текущий side-sweep lifecycle;
17. точное условие despawn side obstacle;
18. почему side obstacle исчезает в середине;
19. где MP4-фон и дорога визуально разрываются;
20. чего не хватает относительно референса по глубине и hit feedback.

Добавь в аудит контактные листы current/reference и конкретные timecodes.

---

# 2. BLENDER И BLENDER MCP — УСТАНОВКА И ПРОВЕРКА

## 2.1. Blender уже установлен

Исходи из того, что Blender установлен на Windows-компьютере пользователя. Сначала найди executable автоматически в типичных местах:

```text
C:\Program Files\Blender Foundation\Blender *\blender.exe
C:\Program Files\Blender Foundation\Blender\blender.exe
```

Дополнительно проверь PATH и Godot editor setting для Blender.

Сохрани найденный путь в локальную конфигурацию проекта, не в жёсткий абсолютный путь внутри исходного кода.

## 2.2. Blender MCP обязателен к попытке установки

Проверь текущую MCP-конфигурацию Codex и наличие Blender tools.

Предпочтительный порядок:

### Вариант A — production-oriented MCP

Сначала рассмотри `PatrykIti/blender-ai-mcp`, потому что он ориентирован на Codex/MCP clients, предлагает curated tools, goal-first routing и verification. Перед установкой:

- прочитай README;
- прочитай SECURITY.md;
- проверь лицензию;
- проверь совместимость с текущей версией Blender;
- зафиксируй commit SHA;
- включи только localhost-доступ;
- не открывай MCP наружу в сеть;
- не включай ненужные remote/external asset integrations.

### Вариант B — mature fallback

Если вариант A невозможно установить в текущей среде, используй `ahujasid/blender-mcp`, но:

- закрепи конкретный проверенный commit;
- прочитай README и открытые security issues;
- используй только localhost socket;
- не загружай непроверенные модели из внешних источников;
- не включай внешние генераторы 3D и telemetry, если они не нужны;
- помни, что MCP может исполнять Python внутри Blender.

### Вариант C — Codex-specific lightweight fallback

Если A/B несовместимы с Codex environment, допускается `hassledzebra/codex_blender_mcp` после проверки кода, лицензии и конфигурации.

## 2.3. Безопасность

Blender MCP фактически даёт агенту возможность управлять Blender и часто выполнять Python-код. Поэтому:

- слушать только `127.0.0.1`;
- не принимать внешние подключения;
- не открывать произвольные `.blend` из ненадёжных источников;
- не выполнять неизвестные скрипты;
- не загружать внешние модели без необходимости;
- сохранять все сгенерированные исходники в репозитории;
- логировать команды/операции в отчёте;
- не удалять пользовательские файлы вне проектной папки.

## 2.4. Если MCP невозможно завершить автоматически

Не блокируй работу. Создай Blender Python pipeline и запускай Blender через CLI:

```powershell
"<BLENDER_PATH>" --background --python scripts/blender/build_visual_assets_v6.py
```

MCP предпочтителен для итеративной визуальной проверки, но **Blender CLI является обязательным рабочим fallback**.

## 2.5. Результаты установки

Создай:

```text
docs/BLENDER_MCP_SETUP_V6.md
scripts/setup_blender_mcp_v6.ps1
scripts/verify_blender_pipeline_v6.ps1
```

Отчёт должен включать:

- найденную версию Blender;
- найденный executable;
- выбранный MCP;
- commit SHA;
- способ запуска;
- результат connection test;
- viewport capture test;
- fallback Blender CLI test;
- ограничения и security notes.

---

# 3. ЕДИНАЯ ART DIRECTION

## 3.1. Стиль

Создай визуальный стиль:

```text
stylized neon sci-fi cardio corridor
clean low-poly forms
solid translucent cores
emissive edges
clear silhouettes
high readability
controlled cyan / magenta / amber accents
```

Не использовать:

- чистый wireframe как основной материал обязательного cue;
- слишком тонкие рамки;
- мелкие декоративные детали;
- фотореалистичные объекты;
- копию ассетов референса;
- текст внутри обязательных cue;
- цвет как единственный способ различить действие.

## 3.2. Визуальная иерархия

Приоритет в каждом кадре:

1. mandatory active cue;
2. execution deck / judgment zone;
3. next preview cue;
4. road and lane direction;
5. performer safe zone;
6. MP4 background;
7. decorative particles and accents.

## 3.3. Цвет

Базовая палитра может использовать существующие cyan/magenta цвета, но смысл передаётся сначала формой.

Предлагаемый coding:

- steps/travel: cyan или magenta по lane/side;
- hand targets: bright white + amber/cyan accent;
- jumps: magenta/white floor energy;
- duck/squat: amber/orange overhead structure;
- hold/freeze: violet circular frame;
- side sweep: large translucent magenta/cyan prism.

Все значения вынести в визуальный конфиг.

Создай:

```text
data/visual_style_v6.json
```

---

# 4. ГЕНЕРАЦИЯ 2D-ИЗОБРАЖЕНИЙ И ПИКТОГРАММ

Codex умеет генерировать изображения. Используй это для создания оригинального набора cue icons, decals и вспомогательных текстур.

## 4.1. Общие требования

Все изображения:

- оригинальные;
- не копируют графику конкурента;
- прозрачный фон;
- без текста и букв;
- без водяных знаков;
- чистый силуэт;
- хорошо читаются при уменьшении;
- квадратный master 1024×1024;
- финальные игровые версии 512×512 или 256×256;
- alpha premultiplication проверена;
- края без белой/чёрной каймы;
- сохраняются как PNG/WebP, подходящий текущему импорту Godot.

Сохрани generation prompts и negative prompts:

```text
assets/generated/v6/prompts/
assets/generated/v6/source/
assets/generated/v6/final/
```

## 4.2. Обязательные изображения

Создай минимум:

```text
footprint_left.png
footprint_right.png
footprint_center.png
arrow_left.png
arrow_right.png
arrow_forward.png
punch_left_icon.png
punch_right_icon.png
double_punch_icon.png
clap_icon.png
open_arms_icon.png
jump_icon.png
duck_icon.png
squat_icon.png
lean_left_icon.png
lean_right_icon.png
hold_icon.png
pose_icon.png
```

## 4.3. Master prompts для генерации

### Footprint left

```text
Single stylized LEFT athletic sneaker footprint pictogram, strict top-down orthographic view, toe pointing to the top of the image, anatomically correct left shoe sole, bold clean silhouette, futuristic fitness game icon, white core with subtle cyan inner sole details, thick readable shapes, transparent background, centered, no text, no letters, no extra objects, game UI decal, high contrast
```

### Footprint right

```text
Single stylized RIGHT athletic sneaker footprint pictogram, strict top-down orthographic view, toe pointing to the top of the image, anatomically correct right shoe sole, bold clean silhouette, futuristic fitness game icon, white core with subtle magenta inner sole details, thick readable shapes, transparent background, centered, no text, no letters, no extra objects, game UI decal, high contrast
```

Не получать right-footprint автоматическим случайным mirror в Godot. Создай и визуально проверь отдельную right-версию.

### Punch target icon

```text
Single bold futuristic fist impact pictogram for a rhythm fitness game, front-facing simplified boxing fist silhouette, strong central impact shape, white core with cyan energy accents, thick readable icon, transparent background, centered, no text, no letters, no character, no photorealism
```

Для right/left создать отдельные варианты с осмысленной ориентацией.

### Jump icon

```text
Stylized rhythm fitness jump pictogram, two simplified shoe soles lifting above a bright floor wave, bold clean silhouette, energetic upward motion arrows, white and magenta accents, transparent background, centered, no text, no person, no photorealism
```

### Duck/squat icon

```text
Stylized fitness duck-under pictogram, simplified downward body motion symbol beneath an overhead bar, bold readable game icon, white and amber accents, transparent background, no text, no detailed human face, centered
```

### Lean icons

```text
Stylized lean-left movement pictogram for a rhythm fitness game, simplified torso directional symbol, strong leftward motion arrow, bold geometric silhouette, white and cyan accents, transparent background, centered, no text
```

Сделай отдельный lean-right variant.

## 4.4. Texture validation

Создай автоматический contact sheet и проверь:

- alpha bounds;
- left/right semantic correctness;
- no accidental rotation;
- no cropping;
- no text artifacts;
- readable at 64×64;
- readable on cyan/magenta dark backgrounds.

Создай:

```text
output/previews/assets_v6/icon_contact_sheet.png
docs/GENERATED_IMAGE_ASSET_REPORT_V6.md
```

---

# 5. КООРДИНАТЫ, PIVOTS И LANE PLACEMENT

## 5.1. Не угадывай направление

Определи фактическое направление движения из road/controller/camera code.

Создай debug scene:

```text
scenes/debug/CoordinateOrientationTestV6.tscn
```

В ней показать:

- world X/Y/Z arrows;
- camera forward;
- road forward;
- cue travel direction;
- lane centers;
- judgment plane;
- left/right labels только в debug scene.

## 5.2. Единый contract placement

Введи структуру:

```text
CuePlacementProfile
- lane_index
- lane_center_x
- lane_width
- width_ratio
- ground_offset
- pivot_mode
- visual_forward_axis
- spawn_z
- judgment_z
- despawn_z
- safe_zone_policy
```

Обязательные cue должны использовать один placement service, а не каждый собственную формулу.

## 5.3. Pivot rules

- ground cue pivot: bottom center at road surface;
- flying cube pivot: geometric center;
- overhead gate pivot: center of safe opening or documented anchor;
- side sweep pivot: geometric center with explicit bounding box;
- floor wave pivot: center on road plane;
- decal/pictogram plane: slightly above surface to avoid z-fighting.

## 5.4. Запрет negative scale для semantic mirror

Не использовать `scale.x = -1` для footprint/icon variants, если это может ломать:

- normals;
- culling;
- UV;
- icon anatomy;
- material direction;
- exported transforms.

Использовать отдельные left/right assets или проверенный rotation/variant mapping.

---

# 6. BLENDER ASSET PIPELINE

Создай структуру:

```text
assets/blender/v6/source/
assets/blender/v6/exports/
assets/blender/v6/previews/
scripts/blender/build_visual_assets_v6.py
scripts/blender/export_visual_assets_v6.py
```

## 6.1. Общие требования моделей

- low-poly stylized;
- clean silhouette;
- consistent real scale;
- apply transforms;
- correct normals;
- backface culling compatible;
- no unapplied negative scales;
- origin/pivot documented;
- 1–3 material slots максимум на простой cue;
- emissive material slot separated;
- UV только там, где нужна иконка;
- no hidden geometry;
- no unnecessary lights/cameras;
- efficient instancing;
- exports as `.glb` (preferred);
- source `.blend` saved;
- imported Godot scenes/resources generated without manual steps.

Godot lighting настраивай в Godot, а не полагайся на Blender lights.

## 6.2. Обязательный asset set

Создай:

```text
step_pad_left.blend / .glb
step_pad_right.blend / .glb
step_pad_center.blend / .glb
icon_cube_target.blend / .glb
icon_cube_shards.blend / .glb
side_sweep_block_left.blend / .glb
side_sweep_block_right.blend / .glb
overhead_gate.blend / .glb
duck_gate.blend / .glb
jump_wave_small.blend / .glb
jump_wave_large.blend / .glb
hold_ring.blend / .glb
pose_frame.blend / .glb
```

---

# 7. STEP PAD V2 — ПОЛНАЯ ПЕРЕРАБОТКА

## 7.1. Внешний вид

Step pad должен быть не просто плоским прямоугольником.

Состав:

- beveled low-profile platform;
- solid translucent dark core;
- emissive outer rim;
- recessed icon area;
- footprint decal;
- subtle directional chevron;
- optional small lane-side notch.

Примерные пропорции относительно lane:

- width: 0.68–0.78 lane width;
- depth: 0.55–0.75 lane width;
- height: 0.04–0.09 lane width;
- footprint occupies 45–60% of top face.

Не хардкодить абсолютные размеры, привязать к lane width.

## 7.2. Правильная ориентация следов

Определи визуальный forward по reference и world direction. В texture-space toe может смотреть вверх, но final world orientation должна быть подтверждена debug test.

Создай отдельные left/right models или material variants.

Проверить:

```text
STEP_LEFT  → left footprint
STEP_RIGHT → right footprint
```

Не доверять только имени файла. Сделать screenshot-based audit.

## 7.3. Анимация

- spawn: soft scale/fade, без резкого pop;
- approach: stable;
- pre-hit: rim pulse;
- hit: platform flash + footprint flare;
- feedback: short particles/afterglow;
- despawn: dissolve after crossing judgment plane.

## 7.4. Acceptance

- следы не перевёрнуты;
- left/right не перепутаны;
- pad ровно сидит на road plane;
- icon не z-fight;
- cue читается без debug text;
- в 720p footprint читается на instruction_time.

---

# 8. ICON CUBE TARGET — ЗАМЕНА СФЕРЫ

## 8.1. Концепция

Заменить непонятный шар/сферу на небольшой объёмный летящий **Icon Cube Target**.

Куб обозначает hand/action target. Он летит к judgment area, содержит понятную сгенерированную пиктограмму и разрушается при hit.

## 8.2. Геометрия

Состав intact cube:

1. bevelled outer cube frame;
2. semi-transparent inner core;
3. front icon panel slightly inset;
4. emissive corner accents;
5. optional thin back panel;
6. clear front-facing orientation.

Пример:

- cube size: 0.35–0.55 lane width;
- bevel: заметный, но не игрушечный;
- frame thickness: 5–10% cube size;
- icon panel: 55–70% front face;
- no tiny subdivisions.

## 8.3. Image insert

Icon texture выбирается по movement:

```text
PUNCH_LEFT      → punch_left_icon
PUNCH_RIGHT     → punch_right_icon
DOUBLE_PUNCH    → double_punch_icon
CLAP            → clap_icon
OPEN_ARMS       → open_arms_icon
```

Изображение должно быть внутри/на внутренней front plane, а не просто billboard вне куба.

## 8.4. Ориентация

Куб должен постоянно быть читаем камерой:

- либо front face ориентирована вдоль movement path;
- либо используется constrained look-at только по Y-axis без нежелательного roll;
- icon не должен отображаться зеркально;
- left/right icon variants проверяются отдельно.

## 8.5. Hit destruction

Не делай дорогой runtime fracture.

Предпочтительная реализация:

- intact cube visible до hit;
- заранее подготовленный Blender `shards_root` из 10–20 крупных фрагментов;
- при hit intact cube скрывается;
- shards становятся видимыми;
- получают детерминированные radial velocities;
- emissive burst + particles;
- shards fade за 0.25–0.45 секунды;
- pool reset восстанавливает transforms.

Допустим simpler fallback:

- 8 corner shards + 6 face shards;
- не менее 10 читаемых фрагментов;
- не использовать сотни физических rigid bodies.

## 8.6. Physics/performance

- не использовать полноценную физическую симуляцию, если она нарушает deterministic render;
- shard trajectories рассчитывать вручную или через deterministic tween;
- object pooling обязателен;
- одинаковый seed даёт одинаковый burst.

## 8.7. Lifecycle

```text
SPAWN
→ PREVIEW
→ APPROACH
→ PRE_HIT_PULSE
→ HIT_SHATTER
→ SHARD_FADE
→ RESET_TO_POOL
```

## 8.8. Acceptance

- шар заменён cube target там, где semantic = hand/action target;
- куб объёмный и читаемый;
- иконка не зеркальна;
- hit вызывает явное разрушение;
- destruction совпадает с hit_time в пределах одного кадра;
- shards не остаются в сцене;
- cube не выглядит как плоский UI billboard.

---

# 9. SIDE SWEEP OBSTACLE V2 — ОБЪЁМ И ПРАВИЛЬНЫЙ ПРОЛЁТ

## 9.1. Проблема

Текущий большой боковой obstacle:

- похож на тонкую плоскость/сетку;
- не имеет убедительной массы;
- слабо показывает безопасную сторону;
- иногда исчезает в середине кадра;
- despawn связан с hit_time или центральной точкой, а не с реальным выходом объекта.

## 9.2. Новая концепция

Создай два variants:

```text
side_sweep_block_left
side_sweep_block_right
```

Это крупный объёмный semi-transparent energy prism / wall module, который занимает запрещённую часть corridor и физически проносится мимо камеры.

## 9.3. Геометрия

Obstacle должен иметь:

- настоящую толщину;
- solid translucent core;
- bevelled emissive edge frame;
- 2–4 крупных внутренних ribs;
- direction streaks;
- trailing edge glow;
- clear blocked zone;
- clear safe gap.

Не использовать только wireframe.

Размер строить от lane geometry:

- width — блокирует нужное количество lane;
- height — выходит заметно выше рабочей зоны;
- depth/thickness — достаточная, чтобы объект ощущался объёмным при пролёте;
- safe corridor — не уже минимальной ширины движения.

## 9.4. Semantics

Чётко определить naming:

- `SIDE_SWEEP_FROM_LEFT` означает obstacle приходит/занимает левую часть и пользователь уходит вправо;
- `SIDE_SWEEP_FROM_RIGHT` означает obstacle приходит/занимает правую часть и пользователь уходит влево.

Не смешивать:

- сторону источника obstacle;
- сторону blocked area;
- сторону required body movement.

В JSON сохранить отдельные поля:

```json
{
  "source_side": "right",
  "blocked_side": "right",
  "required_move": "left"
}
```

## 9.5. Lifecycle и despawn

Обязательный lifecycle:

```text
SPAWN_FAR
→ APPROACH
→ ENTER_ACTIVE_CORRIDOR
→ CROSS_JUDGMENT_ZONE
→ PASS_CAMERA
→ FULLY_EXIT_FRUSTUM
→ DESPAWN
```

Запрещено despawn по одному только `hit_time`.

Despawn разрешён только когда выполняется одно из условий:

1. world-space bounding box полностью прошёл camera/pass plane с margin;
2. obstacle полностью за камерой и вне активного frustum;
3. safety timeout после прохождения камеры, но не до него.

Добавить поле:

```text
post_hit_pass_duration
```

Obstacle должен быть виден после hit, пока реально пролетает мимо.

## 9.6. Motion

- движение плавное и предсказуемое;
- no mid-path teleport;
- no sudden scale collapse;
- no alpha zero before passing camera;
- optional slight lateral sweep only if semantic требует;
- forward travel должен совпадать с остальными cue.

## 9.7. Visual feedback

При прохождении рядом с камерой:

- edge streak;
- brief side light wash;
- very mild camera-side pulse;
- no strong full-screen flash;
- no clipping through execution deck.

## 9.8. Debug validation

В QA mode показать:

- bounding box;
- source side;
- blocked side;
- required move;
- judgment crossing time;
- camera pass plane;
- despawn plane;
- current lifecycle state.

## 9.9. Acceptance

- obstacle выглядит объёмным;
- безопасная сторона понятна;
- left/right semantics правильны;
- он не исчезает в центре;
- объект проходит judgment zone;
- продолжает движение мимо камеры;
- despawn происходит только после выхода;
- нет pop/disappearance.

---

# 10. JUMP, DUCK, HOLD И ДРУГИЕ CUE — ЕДИНЫЙ PASS

После трёх главных исправлений обнови остальные обязательные cue, чтобы они соответствовали одному visual language.

## Jump wave

- low floor wave;
- solid luminous band, не тонкая линия;
- видна издалека;
- идёт поперёк активного corridor;
- clearly different from step pad;
- hit triggers floor ripple.

## Overhead/duck gate

- real volume and thickness;
- clear opening below;
- amber/orange accents;
- не похож на side wall;
- passes over/through camera before despawn if moving object.

## Hold ring / pose frame

- ring/frame with duration progress;
- stationary relative to judgment zone or documented behavior;
- не использовать как замену step/punch;
- clear hold duration.

## Lean cue

- volumetric side wave or angled prism;
- safe side visible;
- source/required direction fields explicit;
- no sudden disappearance.

---

# 11. EXECUTION DECK V3

Нижняя рабочая зона должна быть сильной, но не перегруженной.

Добавь:

- three lane pads or current lane count;
- dark translucent surface;
- controlled emissive outlines;
- persistent judgment line;
- active lane highlight;
- short hit afterglow;
- subtle downbeat pulse;
- readable separation from black road.

Execution deck не должна заслонять footprints.

Она должна объяснять:

```text
cue reaches this line = execute movement now
```

Вынеси настройки в:

```text
data/execution_deck_profile_v6.json
```

---

# 12. ROAD MATERIAL V3 И СКЛЕЙКА С MP4

Не менять существующий MP4 playback.

## 12.1. Road material

Сделай дорожку не абсолютной чёрной пустотой:

- dark base;
- subtle surface texture;
- emissive lane lines;
- edge rails;
- very mild reflection/color response;
- scrolling micro-streaks;
- fade toward horizon;
- no excessive mirror/gloss.

## 12.2. Horizon integration

Убрать жёсткий визуальный шов между MP4 и road:

- soft horizon fog;
- gradient blend;
- color pickup from current background palette;
- faint side supports/rails;
- controlled haze;
- no need to modify/re-encode MP4.

## 12.3. Background readability control

Во время сложного mandatory cue допускается локально/временно:

- слегка снизить intensity background presentation layer;
- усилить cue rim;
- уменьшить secondary particles;
- увеличить local contrast.

Не затемнять MP4 постоянно.

---

# 13. DEPTH STAGING И ПЕРСПЕКТИВА

В кадре должны читаться слои:

```text
execution deck
→ active cue
→ preview cue
→ road/horizon support
→ MP4 background
```

## Rules

- far cue slightly dimmer but still readable;
- approaching cue gets stronger rim and contrast;
- no sudden scale changes;
- same archetype preserves consistent world scale;
- mandatory cue on instruction_time should occupy enough pixels.

## QA metrics at 1280×720

Настраиваемые ориентиры:

- critical icon minimum visible bound at instruction_time: около 42–64 px;
- active cue contrast against local background: measurable and documented;
- no two mandatory cue silhouettes overlap more than configured threshold;
- safe-zone overlap = 0.

Не использовать эти значения слепо: проверить визуально и вынести в config.

---

# 14. HIT FEEDBACK SYSTEM V3

## 14.1. Lifecycle

Все cue используют единый lifecycle API:

```text
spawn
preview
approach
pre_hit
hit
feedback
post_hit_pass / dissolve
reset
```

## 14.2. Feedback tiers

### LIGHT

- lane flash;
- 6–12 small particles;
- short emissive spike;
- 80–140 ms afterglow.

### STRONG / DOWNBEAT

- stronger floor pulse;
- 12–24 particles;
- small FOV pulse;
- edge response;
- 120–200 ms.

### PHRASE / SIGNATURE

- larger controlled burst;
- road-edge wave;
- background support pulse;
- no full-screen white flash;
- camera motion remains readable.

## 14.3. Cue-specific feedback

- step: pad flare + footprint flash;
- cube: shatter;
- sweep wall: side pass streak;
- jump: floor ripple;
- duck gate: overhead energy trail;
- hold: completion ring.

## 14.4. Timing

Effect start must equal `hit_time` within one rendered frame.

---

# 15. SECTION-BASED VISUAL DRAMATURGY

Один MP4 может оставаться тем же, но additive layers должны меняться по section/energy.

Создай profiles:

```text
CALM
GROOVE
BUILD
PEAK
RECOVERY
FINAL
```

Они управляют:

- road emissive;
- speed streak strength;
- particle density;
- fog/haze;
- cue glow multiplier;
- hit feedback tier multiplier;
- side rail response;
- camera FOV pulse;
- color accent mix.

## Profile behavior

### CALM
- clean frame;
- low particles;
- large readable cues;
- gentle road glow.

### GROOVE
- stable pulse;
- moderate streaks;
- normal hit feedback.

### BUILD
- increasing streak speed;
- brighter rails;
- stronger pre-hit pulse.

### PEAK
- strongest controlled feedback;
- larger signature accents;
- no readability loss.

### RECOVERY
- reduced density;
- softer road;
- longer clean visual gaps.

### FINAL
- return signature look;
- strong final cue;
- clear ending pose/hold.

---

# 16. CAMERA POLISH

Не менять композицию радикально.

Разрешены:

- subtle FOV pulse;
- tiny phrase push;
- mild camera bob on strong accents;
- side light reaction when wall passes.

Запрещены:

- chaotic shake;
- roll rotations;
- rapid lateral camera movement;
- changes that move mandatory cues into performer safe zone;
- motion that makes step pads unreadable.

---

# 17. PERFORMANCE И DETERMINISM

## Requirements

- object pooling for all recurring cue;
- cube shards pooled;
- deterministic burst trajectories;
- no unbounded particle accumulation;
- no runtime external image generation;
- generated assets baked before render;
- stable 30 FPS frame-locked output;
- QA and clean have identical event timing;
- avoid heavy realtime fracture/physics;
- report draw calls/instance count where possible.

## Godot import

Предпочтительно экспортировать Blender assets как `.glb`. Допускается `.blend` direct import, но final reproducible pipeline должен работать на clean checkout с documented Blender path. Проверить materials, culling, emissive import и pivots.

---

# 18. ТЕСТОВЫЕ СЦЕНЫ

Создай:

```text
scenes/debug/CoordinateOrientationTestV6.tscn
scenes/debug/CueAssetGalleryV6.tscn
scenes/debug/CueOrientationPairsV6.tscn
scenes/debug/CubeShatterTestV6.tscn
scenes/debug/SideSweepLifecycleTestV6.tscn
scenes/debug/ExecutionDeckTestV6.tscn
```

## CueAssetGallery

Показывает все cue:

- front;
- perspective;
- far-distance;
- active-distance;
- hit state.

## CueOrientationPairs

Показывает рядом:

- step left/right;
- punch left/right;
- lean left/right;
- side sweep left/right;
- world-forward arrow;
- required movement arrow.

## SideSweepLifecycleTest

Должен автоматически прогонять obstacle до полного pass-camera и писать state/time log.

---

# 19. VISUAL VALIDATOR V6

Добавь автоматические проверки.

## Hard errors

- missing cue asset;
- missing left/right variant;
- negative scale on semantic icon node;
- footprint mapping mismatch;
- cue pivot outside documented tolerance;
- ground cue floating/clipping beyond tolerance;
- mandatory cue safe-zone overlap;
- side obstacle despawn before pass-camera plane;
- cube hit without shard reset;
- hit feedback > 1 frame error;
- missing texture alpha;
- invalid GLB import;
- QA/clean frame count mismatch.

## Warnings

- cue too small at instruction_time;
- local contrast too low;
- too much wireframe/transparency;
- large cue hides next mandatory cue;
- particles obscure icon;
- road/background seam visible;
- section profile causes overexposure;
- too many simultaneous emissive effects.

Сохрани:

```text
output/reports/visual_validation_v6.json
```

---

# 20. ПОЭТАПНЫЙ ПОРЯДОК ВЫПОЛНЕНИЯ

Работай строго по sprint gates. Не делать всё хаотично.

## SPRINT V6-A — Orientation and placement

1. Audit.
2. Blender/MCP setup.
3. Coordinate test.
4. Fix footprints.
5. Fix left/right mapping.
6. Fix lane/pivot placement.
7. Render 15–20 sec QA test.

Gate:

- footprints correct;
- no lane offset;
- no negative semantic mirror;
- no floating pads.

## SPRINT V6-B — Icon cube

1. Generate icons.
2. Build cube intact/shards in Blender.
3. Import into Godot.
4. Map punch/action semantics.
5. Implement deterministic shatter.
6. Render close/far/hit tests.

Gate:

- sphere removed for target semantics;
- cube readable;
- icon correct;
- shatter works and resets.

## SPRINT V6-C — Side sweep

1. Build volumetric left/right wall assets.
2. Clarify source/blocked/required semantics.
3. Rewrite lifecycle/despawn only for visual movement.
4. Add pass-camera state.
5. Render dedicated lifecycle test.

Gate:

- no mid-screen disappearance;
- safe side clear;
- object passes camera.

## SPRINT V6-D — Whole cue language

1. Upgrade jump/duck/hold/lean.
2. Execution deck.
3. Unified materials.
4. Asset gallery.

Gate:

- cue categories distinguishable without text.

## SPRINT V6-E — Integration and polish

1. Road material.
2. Horizon blend.
3. Hit feedback.
4. Section profiles.
5. Mild camera polish.
6. Full 45–60 sec render.

Gate:

- visual hierarchy and reference-level clarity improved.

---

# 21. ОБЯЗАТЕЛЬНЫЕ DELIVERABLES

## Renders

```text
output/renders/vertical_slice_visual_v6_qa.avi
output/renders/vertical_slice_visual_v6_clean.avi
```

Длительность: 45–60 секунд.

Сегмент должен содержать:

- step left;
- step right;
- icon cube action;
- cube shatter;
- side sweep from left;
- side sweep from right;
- jump wave;
- duck/overhead cue;
- hold/pose;
- calm section;
- build/peak section;
- recovery section.

## Preview frames

```text
output/previews/vertical_slice_visual_v6/
```

Минимум:

1. footprint left close;
2. footprint right close;
3. left/right orientation comparison;
4. cube far;
5. cube active;
6. cube shatter;
7. side sweep approach;
8. side sweep crossing judgment zone;
9. side sweep passing camera;
10. jump cue;
11. duck cue;
12. execution deck;
13. calm state;
14. peak state;
15. clean representative frame.

## Asset previews

```text
output/previews/assets_v6/icon_contact_sheet.png
output/previews/assets_v6/blender_asset_contact_sheet.png
```

## Docs

```text
docs/VISUAL_GAP_AUDIT_V6.md
docs/BLENDER_MCP_SETUP_V6.md
docs/GENERATED_IMAGE_ASSET_REPORT_V6.md
docs/BLENDER_ASSET_REPORT_V6.md
docs/VISUAL_IMPLEMENTATION_REPORT_V6.md
```

## Source assets

```text
assets/blender/v6/source/*.blend
assets/blender/v6/exports/*.glb
assets/generated/v6/source/*
assets/generated/v6/final/*
assets/generated/v6/prompts/*
```

## Debug/Reports

```text
output/debug/visual_v6_metrics.json
output/reports/visual_validation_v6.json
output/reports/visual_v6_render_manifest.json
```

---

# 22. ACCEPTANCE CRITERIA — РАБОТА НЕ ПРИНЯТА БЕЗ ВСЕХ ПУНКТОВ

## Orientation

1. Step-left показывает корректный left footprint.
2. Step-right показывает корректный right footprint.
3. Следы не повёрнуты в неверную сторону относительно road-forward.
4. Нет negative scale на semantic icon/footprint nodes.
5. Left/right pairs подтверждены contact sheet.

## Cube

6. Непонятная сфера больше не используется как основной hand/action target.
7. Cube target выглядит объёмно.
8. Внутри/на inner face видна оригинальная сгенерированная пиктограмма.
9. Иконка не зеркальна.
10. Cube shatter начинается точно на hit_time.
11. Shards детерминированы и возвращаются в pool.

## Side sweep

12. Side obstacle имеет настоящую толщину.
13. Он не выглядит как одна тонкая сетка.
14. Safe side понятна без debug text.
15. Source/blocked/required sides не перепутаны.
16. Obstacle не исчезает в середине кадра.
17. Он проходит judgment zone.
18. Он продолжает движение мимо камеры.
19. Despawn происходит только после полного выхода.

## Placement

20. Все ground cue уверенно стоят на road plane.
21. Cue выровнены по lane centers.
22. Нет непреднамеренного clipping/floating.
23. Mandatory cue не входят в performer safe zone.

## Readability

24. Step, cube/punch, jump, duck и side sweep различимы без QA-текста.
25. Mandatory cue читаются издали.
26. Cue не теряются на MP4 фоне.
27. Execution deck ясно показывает момент исполнения.
28. Hit feedback заметен, но не закрывает cue.

## Visual integration

29. Дорожка не выглядит отдельной чёрной плоскостью.
30. Horizon seam смягчён.
31. MP4 и игровая сцена ощущаются одним пространством.
32. Section profiles создают развитие визуала без смены MP4.
33. Результат не копирует художественные ассеты референса.

## Technical

34. Старые JSON-контракты не сломаны.
35. Analyzer GUI не переписан.
36. MP4 integration не переделана.
37. QA и clean имеют одинаковое количество кадров.
38. Hit timing error ≤ 1 frame.
39. No hard visual validator errors.
40. Repeat render with same seed produces deterministic visual timing.

---

# 23. ФИНАЛЬНЫЙ ОТЧЁТ CODEX

После завершения не ограничивайся фразой «готово».

В `docs/VISUAL_IMPLEMENTATION_REPORT_V6.md` укажи:

- что было найдено в аудите;
- почему footprints были перевёрнуты;
- как исправлена ориентация;
- какой Blender MCP выбран и почему;
- как проверялась безопасность/localhost;
- какие картинки были сгенерированы;
- prompts и locations;
- какие Blender assets созданы;
- как реализован cube shatter;
- как исправлен side sweep lifecycle;
- точное новое despawn condition;
- как выполнена интеграция road/MP4;
- результаты visual validator;
- результаты frame/timing validation;
- список изменённых файлов;
- команды запуска тестовых сцен;
- команды создания финального рендера;
- известные ограничения;
- before/after contact sheet.

---

# 24. КОМАНДА НА СТАРТ

Начни не с косметических эффектов, а в следующем порядке:

```text
AUDIT
→ BLENDER/MCP SETUP
→ COORDINATE TEST
→ FOOTPRINT FIX
→ ICON CUBE + SHATTER
→ SIDE SWEEP LIFECYCLE
→ CUE ASSET PASS
→ EXECUTION DECK
→ ROAD/MP4 INTEGRATION
→ HIT FEEDBACK
→ SECTION PROFILES
→ FINAL QA/CLEAN RENDER
```

Не переходи к road polish и декоративным FX, пока не пройдены три главных gate:

1. footprints полностью корректны;
2. sphere заменена качественным icon cube;
3. side obstacle реально пролетает мимо камеры и больше не исчезает в центре.

