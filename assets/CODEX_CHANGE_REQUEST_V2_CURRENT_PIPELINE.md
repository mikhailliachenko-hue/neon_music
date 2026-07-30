# CODEX CHANGE REQUEST V2
## Доработка существующего Dance Video Pipeline без переписывания рабочего анализатора

> Этот документ предназначен для передачи Codex как основное техническое задание. Сначала изучи существующий репозиторий, затем выполняй изменения поэтапно. Не создавай новый проект с нуля и не ломай текущий Analyzer GUI, если он уже корректно анализирует музыку и создаёт JSON.

---

# 0. Контекст задачи

У пользователя уже существует рабочий pipeline:

1. музыкальный файл загружается в отдельный Python Analyzer GUI;
2. анализатор создаёт JSON с музыкальной разметкой;
3. в папку `background` кладётся MP4-файл;
4. существующий генератор создаёт перспективную дорожку и визуальные события;
5. итог используется как фон, поверх которого пользователь позже накладывает свою запись в CapCut.

Нужно не переписать систему, а довести её до уровня профессионального интерактивного dance-cardio ролика:

- хореография должна ощущаться как связный танец, а не случайный набор нот;
- препятствия должны однозначно объяснять движение;
- визуал должен реагировать на музыкальные секции;
- дорожка и MP4-фон должны выглядеть единым миром;
- слева должна оставаться безопасная зона для записанного человека;
- результат должен быть похож по качеству и понятности на референс, но иметь собственную художественную идентичность.

---

# 1. Что видно в текущем результате

Исследованный текущий рендер:

- длительность: примерно `171.584 s`;
- разрешение: `1920×1080`;
- частота: `30 FPS`;
- оценочный темп музыки: около `136 BPM`;
- основной фон: один неоновый тоннель на всю композицию;
- дорожка: три перспективные линии/полосы на почти полностью чёрной нижней половине кадра;
- события: бирюзовые и розовые плитки, белые круги/кольца, редкие большие боковые стены и жёлтая зона;
- нет постоянного preview следующего движения;
- нет выраженной секционной драматургии;
- нет заметного hit-feedback в момент исполнения;
- дорожка занимает центральную часть и будет конфликтовать с человеком, которого пользователь наложит слева.

Положительная сторона: грубая автоматическая проверка записи показывает, что крупные визуальные изменения в целом близки к аудио-атакам. Значит, главный приоритет — не переписывать beat detection, а исправить **структуру хореографии, семантику подсказок и визуальную драматургию**.

Отдельная грубая проверка по четырёхсекундным окнам показала практически отсутствующую связь между общей визуальной активностью дорожки и изменением громкости/плотности атак музыки. Это не является точной научной метрикой, но подтверждает визуальное впечатление: сейчас ролик почти одинаково активен на разных музыкальных участках.

---

# 2. Главный диагноз

Текущая система уже умеет делать:

```text
музыкальный момент → отдельное событие → движение объекта по дорожке
```

Но профессиональный ролик требует следующей иерархии:

```text
трек
→ музыкальная секция
→ 32-счётная фраза
→ 8-счётный мотив
→ движение тела
→ заранее понятная визуальная подсказка
→ точный момент исполнения
→ визуальная реакция мира
→ возвращение и развитие мотива позже
```

Основная проблема сейчас не в отсутствии объектов, а в отсутствии **хореографического синтаксиса**.

---

# 3. Критические правки по приоритету

## P0 — обязательно до любых косметических улучшений

1. Добавить phrase-level choreography planner.
2. Сделать однозначное соответствие `movement → visual cue`.
3. Добавить безопасную зону для человека и сместить gameplay corridor вправо.
4. Ввести единый `hit_time` и judgment plane для всех объектов.
5. Привязать плотность, сложность и визуальную интенсивность к секциям музыки.
6. Добавить preview следующего движения.
7. Перестать использовать белые круги на полу для неоднозначных действий.
8. Добавить подготовку, восстановление, зеркальность и ограничения по нагрузке.

## P1 — после исправления хореографии

1. Интегрировать дорогу с MP4-фоном по перспективе, цвету и туману.
2. Убрать ощущение «чёрная дорожка поверх отдельного видео».
3. Добавить section transitions, hit FX и мягкую музыкальную камеру.
4. Добавить визуальные профили intro / verse / build / chorus / breakdown / outro.
5. Добавить clean render и QA render.

## P2 — полировка

1. Разные theme skins препятствий.
2. Автоматическое извлечение палитры MP4.
3. Автоматическая оценка читаемости.
4. A/B-кандидаты хореографии.
5. Частичная перегенерация выбранной фразы.

---

# 4. Не переписывать рабочие части без необходимости

Перед изменениями Codex обязан:

1. найти точку входа Analyzer GUI;
2. найти текущую JSON-схему анализа;
3. найти генератор событий дорожки;
4. найти способ загрузки MP4;
5. найти текущий рендер-процесс;
6. зафиксировать существующие контракты в `docs/CURRENT_PIPELINE_AUDIT.md`;
7. создать `PROGRESS.md`;
8. сохранить обратную совместимость со старыми JSON, добавляя default values.

Если beat/downbeat-анализ работает, не заменять его новой библиотекой. Добавить адаптер и post-processing слой.

---

# 5. Хореографический движок V2

## 5.1. Разделить понятия beat event и movement event

Сейчас музыкальный акцент, вероятно, почти напрямую становится объектом. Это нужно изменить.

### Beat event
Содержит музыкальные признаки:

```json
{
  "time": 31.235,
  "beat_index": 68,
  "bar_index": 17,
  "beat_in_bar": 1,
  "downbeat": true,
  "onset_strength": 0.84,
  "energy": 0.72,
  "bass": 0.91,
  "section_id": "chorus_1"
}
```

### Movement event
Содержит человеческое действие:

```json
{
  "id": "move_00142",
  "movement": "STEP_TOUCH_LEFT",
  "instruction_time": 29.470,
  "hit_time": 31.235,
  "duration_beats": 2,
  "lead_beats": 4,
  "phrase_id": "chorus_1_phrase_01",
  "motif_id": "signature_A",
  "side": "left",
  "intensity": 0.58,
  "difficulty": 1,
  "is_new": false,
  "is_mirrored": false
}
```

Не каждый beat обязан создавать новое movement event. Один movement может занимать 2, 4 или 8 долей, а внутренние доли могут управлять пульсацией и небольшими акцентами.

---

## 5.2. Музыкальная сетка

Для обычной музыки 4/4 использовать:

```text
1 такт = 4 beats
1 восьмёрка = 8 beats
1 основная fitness-фраза = 32 beats = 4 × 8 counts
```

При `136 BPM`:

- 1 beat ≈ `0.441 s`;
- 2 beats ≈ `0.882 s`;
- 4 beats ≈ `1.765 s`;
- 8 beats ≈ `3.529 s`;
- 32 beats ≈ `14.118 s`.

Все основные фразы должны начинаться на уверенном downbeat. При сомнительном downbeat разрешается ручной phrase offset в GUI.

Добавить настройки:

```json
{
  "phrase_length_beats": 32,
  "subphrase_length_beats": 8,
  "manual_downbeat_offset_seconds": 0.0,
  "allow_crooked_phrase": false
}
```

---

## 5.3. Главный алгоритм хореографии

Генерация должна проходить в четыре уровня:

### Уровень A — Global Section Planner

Для каждой секции определить:

- роль секции;
- целевую интенсивность;
- плотность действий;
- допустимые категории движений;
- число новых движений;
- camera/FX profile;
- необходимость signature combo.

### Уровень B — Phrase Planner

Каждую 32-счётную фразу строить по одному из шаблонов.

#### Шаблон обучения

```text
8 counts: TEACH A
8 counts: REPEAT A
8 counts: MIRROR A
8 counts: COMBINE A + известное движение
```

#### Шаблон знакомой фразы

```text
8 counts: MOTIF A
8 counts: MIRROR A
8 counts: VARIATION B
8 counts: CALLBACK A'
```

#### Шаблон припева

```text
16 counts: SIGNATURE COMBO
16 counts: SIGNATURE COMBO повторно с 15–30% вариации
```

#### Шаблон восстановления

```text
8 counts: BASE GROOVE
8 counts: UPPER BODY
8 counts: BASE GROOVE + дыхание/раскрытие
8 counts: подготовка следующей секции
```

### Уровень C — Candidate Generator

Для каждой фразы генерировать минимум 8 кандидатов, а не один.

### Уровень D — Scoring + Hard Validation

Сначала применить hard constraints, затем выбрать лучший score.

---

## 5.4. Формула оценки кандидата

Использовать ориентировочную формулу:

```text
score =
  0.25 * musicality
+ 0.20 * learnability
+ 0.15 * transition_quality
+ 0.10 * left_right_balance
+ 0.10 * fatigue_safety
+ 0.10 * motif_coherence
+ 0.10 * visual_readability
```

Hard constraints важнее score.

### Hard constraints

- запрещён невозможный мгновенный переход;
- новое составное движение не появляется без обучения;
- не более одного нового базового движения за 8 counts;
- не более двух новых движений за 32 counts на normal;
- после серии прыжков обязательна низкоударная фраза;
- после глубокого squat не ставить немедленно большой jump;
- не ставить два movement events, требующих несовместимых положений тела;
- не оставлять движение только на одной стороне дольше 16–32 counts;
- обязательное движение не должно быть визуально закрыто другим cue;
- section transition не должна происходить посреди 8-count, кроме специально найденного break/stinger.

---

# 6. Библиотека движений

Создать расширяемую библиотеку минимум из следующих категорий.

## 6.1. Base groove

- `MARCH_IN_PLACE`
- `BOUNCE`
- `STEP_TOUCH_LEFT`
- `STEP_TOUCH_RIGHT`
- `DOUBLE_STEP_LEFT`
- `DOUBLE_STEP_RIGHT`
- `WIDE_STEP`
- `RESET_CENTER`

## 6.2. Upper body

- `PUNCH_LEFT`
- `PUNCH_RIGHT`
- `DOUBLE_PUNCH`
- `REACH_UP_LEFT`
- `REACH_UP_RIGHT`
- `ARMS_OPEN`
- `ARMS_CLOSE`
- `CLAP`
- `ARM_WAVE_LEFT`
- `ARM_WAVE_RIGHT`

## 6.3. Level changes

- `SMALL_SQUAT`
- `SQUAT`
- `DUCK`
- `RISE_REACH`
- `SMALL_JUMP`
- `JUMP_OPEN`

## 6.4. Body direction

- `LEAN_LEFT`
- `LEAN_RIGHT`
- `SIDE_REACH_LEFT`
- `SIDE_REACH_RIGHT`
- `TORSO_TWIST_LEFT`
- `TORSO_TWIST_RIGHT`

## 6.5. Phrase controls

- `FREEZE`
- `POSE`
- `BASE_RECOVERY`
- `SIGNATURE_COMBO_A`
- `SIGNATURE_COMBO_B`

Каждое движение должно хранить:

```json
{
  "id": "STEP_TOUCH_LEFT",
  "category": "base_groove",
  "difficulty": 1,
  "intensity": 0.32,
  "duration_beats": [2, 4],
  "preferred_start_beats": [1, 3],
  "lead_beats_new": 4,
  "lead_beats_known": 2,
  "mirror": "STEP_TOUCH_RIGHT",
  "preparation_pose": "neutral",
  "end_pose": "weight_left",
  "allowed_previous_tags": ["neutral", "weight_right"],
  "forbidden_previous": ["LEAN_LEFT_DEEP"],
  "fatigue_group": "legs_light",
  "impact_level": "low",
  "cue_archetype": "FOOT_LANE_TARGET"
}
```

---

# 7. Ритмическая плотность

На `136 BPM` не нужно заставлять пользователя менять полнотелое действие на каждой доле.

Использовать:

- 1 beat: мелкий акцент рукой, clap, punch, bounce accent;
- 2 beats: step touch, lean, side reach;
- 4 beats: squat, double step, arms open/close, teach movement;
- 8 beats: составная комбинация, recovery, pose sequence.

Профили плотности:

```json
{
  "intro":       {"macro_action_every_beats": 4, "accent_probability": 0.15},
  "verse":       {"macro_action_every_beats": 2, "accent_probability": 0.25},
  "build":       {"macro_action_every_beats": 2, "accent_probability": 0.50},
  "chorus":      {"macro_action_every_beats": 2, "accent_probability": 0.65},
  "breakdown":   {"macro_action_every_beats": 4, "accent_probability": 0.20},
  "outro":       {"macro_action_every_beats": 4, "accent_probability": 0.10}
}
```

Это не означает монотонность. Внутри движения могут происходить мелкие pulse FX на каждом beat.

---

# 8. Секционная логика

## Intro

- 8–16 counts знакомства с ритмом;
- `MARCH_IN_PLACE`, `BOUNCE`, простые step touch;
- минимум визуального шума;
- показать систему подсказок;
- не начинать сразу со стены или сложного препятствия.

## Verse

- учить motif A;
- 60–70% знакомого материала;
- step touch, punches, reaches;
- повторение и зеркальность.

## Build / Pre-chorus

- уменьшать паузы;
- добавлять alternating punches;
- повышать яркость дороги;
- подготовить signature combo;
- последние 4–8 counts могут содержать freeze/build anticipation.

## Chorus / Drop

- signature combo;
- большой, но понятный визуальный ответ;
- больше полнотелых действий;
- не вводить сразу несколько новых movement IDs;
- крупный FX только после того, как cue уже считан.

## Breakdown

- очистить кадр;
- upper body и recovery;
- меньше прыжков;
- медленные sweeping cues;
- подготовить возвращение chorus.

## Final chorus

- вернуть signature combo;
- добавить 15–30% вариации;
- увеличить visual amplitude, а не физическую сложность до опасного уровня.

## Outro

- снизить плотность;
- финальный pose на уверенном музыкальном акценте;
- удержать pose 4–8 beats;
- не заканчивать случайным одиночным тайлом.

---

# 9. Семантика визуальных подсказок

Текущие круги и плитки выглядят как игровые ноты, но не всегда однозначно объясняют движение тела. Нужно создать визуальный язык, где смысл определяется не только цветом.

## 9.1. Правило четырёх каналов

Каждый cue должен сообщать действие минимум через три из четырёх каналов:

1. форма;
2. положение в пространстве;
3. направление движения/анимации;
4. иконка или короткий glyph.

Цвет — дополнительный канал, а не единственный.

---

## 9.2. Рекомендуемое соответствие

### FOOT_LANE_TARGET
Для step touch и lateral step.

- плоская площадка в нужной lane;
- отпечаток стопы;
- стрелка направления;
- левая/правая сторона определяется с точки зрения зрителя и зеркальной демонстрации.

### HAND_TARGET
Для punches и reaches.

- не размещать круг на полу;
- располагать сферу в 3D на уровне груди/плеча;
- левый punch получает target на соответствующей экранной стороне;
- target увеличивается и пульсирует к hit time.

### OVERHEAD_BAR
Для squat/duck.

- яркая верхняя перекладина;
- безопасное пространство снизу;
- вертикальные стрелки вниз;
- не использовать боковую стену для приседания.

### FLOOR_WAVE
Для jump.

- низкая поперечная волна;
- контрастная линия приближения;
- символ вверх;
- hit event, когда волна достигает judgment plane.

### SIDE_SWEEP_WALL
Для lean/side shift.

- стена идёт с противоположной стороны, выталкивая тело в безопасную сторону;
- на безопасной стороне показывается крупный просвет;
- стрелка движения;
- не заливать всю дорожку жёлтым без объяснения.

### DOUBLE_TARGET
Для clap, double punch, arms open.

- два симметричных объекта;
- траектории показывают, должны ли руки сходиться или расходиться.

### FREEZE_RING
Для freeze/pose.

- кольцо замедляется и фиксируется вокруг judgment zone;
- cue не похож на обычную foot note;
- удержание показывается дугой или duration ribbon.

---

# 10. Mirror logic — критически важная правка

Так как пользователь будет записан лицом к зрителю, стороны могут путаться.

В данных разделить:

```text
body_side       — физическая сторона исполнителя
screen_side     — сторона экрана
viewer_action   — движение, которое повторяет зритель
mirror_mode     — зеркально ли показан инструктор
```

Пример:

```json
{
  "movement": "PUNCH_RIGHT",
  "body_side": "right",
  "screen_side": "left",
  "mirror_mode": true,
  "viewer_instruction": "right"
}
```

Нельзя хранить одно поле `side` и использовать его одновременно для тела, экрана и lane.

Добавить визуальный mirror test в редактор.

---

# 11. Время появления подсказок

Использовать формулу:

```text
spawn_time = hit_time - lead_beats × 60 / local_bpm
```

Рекомендации для normal:

- повторяющееся простое движение: `2 beats`;
- новое простое движение: `4 beats`;
- сложное/составное движение: `8 beats`;
- section transition preview: `8–16 beats`.

На 136 BPM это примерно:

- 2 beats: `0.882 s`;
- 4 beats: `1.765 s`;
- 8 beats: `3.529 s`.

Cue может появиться далеко заранее, но должен стать отчётливо читаемым не позднее `4 beats` до исполнения.

---

# 12. Judgment plane и hit feedback

Сейчас момент, когда объект нужно «исполнить», недостаточно подчёркнут.

Добавить невидимую логическую плоскость `JudgmentPlane3D` и видимую мягкую линию/зону в нижней части gameplay corridor.

Требования:

1. передний край cue достигает judgment plane точно в `hit_time`;
2. в hit time cue исчезает, растворяется или преобразуется;
3. происходит короткий impact FX;
4. lane подсвечивается на 100–180 ms;
5. мир получает небольшой pulse;
6. final clean render не добавляет искусственный hitsound поверх музыки, если это не включено отдельно.

Пример FX:

```json
{
  "hit_flash_ms": 120,
  "particle_lifetime_ms": 420,
  "lane_emission_multiplier": 1.65,
  "camera_impulse": 0.04,
  "background_pulse": 0.08
}
```

---

# 13. Next-move preview

Реальный человек, наложенный в CapCut, показывает текущее движение, но зрителю всё равно нужна предварительная информация.

Добавить небольшой `NextMoveCard`:

- располагается над/рядом с instructor zone;
- показывает silhouette/icon следующего движения;
- появляется за 4 beats для нового движения;
- для знакомого движения может появляться за 2 beats;
- отображает направление стрелкой;
- исчезает в hit time;
- может быть отключён в clean minimalist mode.

Не копировать оформление карточки конкурента. Использовать собственную графику.

---

# 14. Композиция кадра и safe zone

Текущая дорожка находится по центру. При наложении человека слева он перекроет важные cues.

Добавить композиционный профиль:

```json
{
  "performer_safe_zone": {
    "side": "left",
    "x": 0.0,
    "y": 0.04,
    "width": 0.24,
    "height": 0.92
  },
  "gameplay_corridor": {
    "center_x": 0.61,
    "bottom_width": 0.58,
    "horizon_x": 0.57,
    "horizon_y": 0.39
  }
}
```

Требования:

- ни один обязательный cue не пересекает safe zone;
- background в safe zone немного спокойнее и темнее;
- декоративные вспышки там ограничены;
- gameplay corridor смещён вправо, но не выглядит обрезанным;
- GUI показывает safe-zone overlay;
- экспортируется `safe_zone_overlay.png`.

---

# 15. Интеграция MP4-фона

Сейчас нижняя часть выглядит как отдельная чёрная плоскость, наложенная поверх видео. Нужно сохранить текущий способ загрузки MP4, но добавить слой калибровки и композитинга.

## 15.1. Background Profile

Для каждого MP4 создавать sidecar JSON:

```json
{
  "source": "background/neon_tunnel.mp4",
  "duration": 18.0,
  "loop_mode": "seamless",
  "horizon_y": 0.41,
  "vanishing_point": [0.52, 0.36],
  "safe_zone_side": "left",
  "safe_zone_busyness": 0.35,
  "dominant_palette": ["#0A0A36", "#153DFF", "#00E8FF", "#EF22DA"],
  "motion_intensity": 0.62,
  "recommended_road_emission": 1.15,
  "recommended_fog": 0.24
}
```

## 15.2. GUI-калибровка

Добавить в Analyzer GUI или отдельный Visual Setup GUI:

- выбрать MP4;
- поставить vanishing point кликом;
- изменить horizon line;
- показать road preview;
- изменить road bottom width;
- выбрать safe zone side;
- проверить loop point;
- сохранить profile JSON.

Автоматическая оценка vanishing point допустима как подсказка, но ручная калибровка должна оставаться.

## 15.3. Визуальное склеивание

Добавить:

- depth fog между дорогой и фоном;
- цветовой градиент road surface;
- мягкое отражение цветов background;
- edge rails;
- emissive lane lines;
- fade на горизонте;
- particles/light streaks, связывающие средний план и дорогу;
- отсутствие резкой горизонтальной границы между MP4 и чёрным полем.

Road surface не должна быть чисто чёрной. Использовать очень тёмный материал с различимой текстурой, отражением и движущимися сегментами.

---

# 16. Вариативность одного MP4

Если пользователь кладёт только один background MP4, не менять скорость его воспроизведения под секции. Это может создать неприятное движение и проблемы с loop.

Вместо этого создавать секционные варианты через:

- LUT/color-grade blend;
- лёгкий zoom/crop 1.00–1.05;
- vignette;
- haze;
- overlay particles;
- road material variant;
- edge lights;
- portal frame;
- controlled exposure pulse.

Профили:

```json
{
  "intro":     {"exposure": 0.88, "particles": 0.20, "road_glow": 0.65},
  "verse":     {"exposure": 0.95, "particles": 0.35, "road_glow": 0.85},
  "build":     {"exposure": 1.02, "particles": 0.55, "road_glow": 1.10},
  "chorus":    {"exposure": 1.08, "particles": 0.80, "road_glow": 1.35},
  "breakdown": {"exposure": 0.82, "particles": 0.15, "road_glow": 0.55},
  "outro":     {"exposure": 0.90, "particles": 0.25, "road_glow": 0.75}
}
```

Все переходы плавные, кроме намеренного drop impact.

---

# 17. Дорожка V2

Текущая дорожка слишком плоская и содержит много пустого чёрного пространства.

Добавить:

1. Road surface mesh или визуально эквивалентную перспективную плоскость.
2. Модульные сегменты, движущиеся к камере.
3. Тонкие поперечные рёбра на beat/bar boundaries.
4. Более яркое ребро на downbeat.
5. Edge rails с отдельной emissive-анимацией.
6. Мягкие отражения cue colors.
7. Fog fade возле horizon.
8. Screen-space проверку размера cue.
9. Object pooling.
10. Разные road profiles по секциям.

Не превращать дорожку в перегруженную нотную сетку. Beat ribs должны быть вторичными.

---

# 18. Камера

Камера должна поддерживать музыку, а не мешать выполнению упражнений.

Разрешённые cues:

- `FOV_BREATHE`: ±2–3%;
- `IMPACT_PUSH`: короткий push на drop;
- `SECTION_REFRAME`: плавное смещение на границе секции;
- `BREAKDOWN_CALM`: уменьшение FOV и motion;
- `PORTAL_DOLLY`: редкий переход между визуальными главами.

Запрещено по умолчанию:

- сильный camera shake;
- частый roll;
- резкие боковые прыжки камеры;
- изменение перспективы, которое меняет смысл lane;
- движение камеры во время обучения нового сложного движения.

---

# 19. FX и визуальная иерархия

Приоритет слоя:

```text
mandatory movement cue
> judgment feedback
> performer/readability
> road navigation
> environment decoration
```

FX должны усиливать важность события, а не закрывать cue.

Добавить:

- hit sparkle;
- lane pulse;
- downbeat road pulse;
- drop shockwave;
- section transition frame;
- subtle background bloom pulse;
- particles after hit, а не перед считыванием.

В последние `0.5 s` до hit mandatory cue не должен перекрываться крупной вспышкой.

---

# 20. HUD и обратная связь

Не копировать чужие combo/perfect badges. Создать собственный минимальный HUD.

Возможные элементы:

- section title;
- next move;
- phrase progress из 4 сегментов;
- energy meter;
- мягкие сообщения `FLOW`, `NICE`, `NEXT COMBO`;
- счётчик выполненных choreographic counts, если нужен декоративный прогресс.

Так как система не отслеживает реального зрителя, не показывать ложное персональное `Perfect` как будто результат измерен.

---

# 21. Режимы экспорта

Добавить минимум три режима:

## QA Preview

- proxy silhouette;
- safe zone;
- current/next movement IDs;
- beat/downbeat markers;
- hit-time debug;
- section name;
- lead-time line.

## Performer Guide

- фон затемнён;
- крупный текущий movement card;
- countdown;
- CSV с timecode;
- optional metronome/click не попадает в clean render.

## Clean Background

- без proxy;
- без debug;
- с safe composition;
- с финальным FX;
- точная длительность музыки.

---

# 22. Редактор

Не обязательно сразу строить сложный DAW. Сначала добавить практический editor panel:

- waveform;
- beat/downbeat grid;
- section blocks;
- phrase blocks по 32 counts;
- movement track;
- obstacle track;
- FX track;
- background profile track;
- lock phrase;
- regenerate phrase;
- mirror phrase;
- simplify phrase;
- increase/decrease intensity;
- preview from 8 beats before selection;
- undo/redo.

Критически важные кнопки:

```text
Simplify Selection
Mirror Selection
Regenerate Unlocked
Teach Before This
Add Recovery
Align to Phrase Start
Validate
```

---

# 23. Валидация

Создать `validation_report.json`.

Проверки:

## Timing

- все hit_time внутри длительности трека;
- все cue arrival совпадают с hit_time;
- нет отрицательного spawn_time;
- section boundaries стоят на beat/downbeat или имеют явный override;
- deterministic render не дрейфует.

## Choreography

- left/right balance;
- repetition count;
- new-movement density;
- fatigue groups;
- jump/squat limits;
- preparation/recovery;
- invalid pose transitions;
- phrase closure на правильной ноге/стороне;
- signature combo consistency.

## Visual

- mandatory cue не находится в safe zone;
- cues не перекрывают друг друга;
- cue имеет минимальный screen-space размер;
- local contrast достаточен;
- wall не закрывает preview card;
- hit feedback не маскирует следующий cue;
- horizon/road profile валиден.

Пример:

```json
{
  "severity": "error",
  "code": "AMBIGUOUS_CUE_MAPPING",
  "event_id": "move_0142",
  "time": 87.235,
  "message": "SIDE_SWEEP_WALL has no safe-side arrow and overlaps yellow floor zone"
}
```

---

# 24. Ограничения нагрузки по умолчанию

Для профиля `normal_general_audience`:

- max больших jumps: 4 за 32 beats;
- max глубоких squats: 2 за 16 beats;
- max high-impact подряд: 8 beats;
- после high-impact: минимум 8 beats low-impact;
- max нового материала: 2 movement IDs за 32 beats;
- side imbalance за 64 beats: не более 15%;
- сложное движение должно иметь 4–8 beats обучения;
- новая signature combo сначала проходит simplified preview.

Сделать `beginner`, `normal`, `active` профили. Не выдавать медицинские обещания.

---

# 25. Псевдокод новой генерации

```python
def generate_choreography(analysis, movement_library, config, seed):
    rng = Random(seed)
    grid = build_phrase_grid(
        beats=analysis.beats,
        downbeats=analysis.downbeats,
        sections=analysis.sections,
        manual_offset=config.manual_downbeat_offset_seconds,
    )

    global_plan = plan_sections(grid, analysis.features, config)
    learned_moves = set(["MARCH_IN_PLACE", "BOUNCE"])
    fatigue_state = FatigueState()
    final_phrases = []

    for phrase in grid.phrases:
        template = select_phrase_template(
            section_role=phrase.section.role,
            learned_moves=learned_moves,
            energy=phrase.energy,
            novelty=phrase.novelty,
        )

        candidates = []
        for _ in range(config.candidate_count):
            candidate = instantiate_template(
                template=template,
                phrase=phrase,
                movement_library=movement_library,
                learned_moves=learned_moves,
                fatigue_state=fatigue_state,
                rng=rng,
            )

            candidate = map_micro_accents(candidate, phrase.audio_accents)
            violations = validate_hard_constraints(candidate, fatigue_state, config)
            if not violations:
                candidate.score = score_candidate(candidate, phrase, config)
                candidates.append(candidate)

        best = max(candidates, key=lambda c: c.score)
        final_phrases.append(best)
        learned_moves.update(best.taught_movements)
        fatigue_state.apply(best)

    choreography = stitch_with_transition_validation(final_phrases)
    obstacles = map_movements_to_visual_cues(choreography, config.visual_language)
    return choreography, obstacles
```

---

# 26. Что конкретно исправить в текущем рендере

## Сейчас

- один тоннель почти без секционных изменений;
- road и background воспринимаются как два отдельных слоя;
- много пустого чёрного пространства;
- cyan/magenta tiles повторяются без выраженных мотивов;
- белые кольца неоднозначны;
- большая боковая стена появляется редко и не объясняет действие;
- жёлтая зона не имеет ясной семантики;
- нет визуального hit moment;
- нет preview следующего движения;
- нет места под исполнителя;
- визуальная плотность почти постоянна;
- нет intro-teach-build-drop-recovery драматургии.

## Должно стать

- corridor смещён вправо;
- слева безопасная зона под человека;
- road интегрирован с фоном;
- movement cue однозначен по форме, положению, направлению и icon;
- каждые 32 beats образуют законченную фразу;
- движения обучаются и возвращаются;
- chorus имеет signature combo;
- breakdown очищает кадр и снижает нагрузку;
- cue приходит заранее;
- hit_time виден по judgment plane и FX;
- background и road меняют интенсивность по секциям;
- final outro заканчивается pose, а не случайной нотой.

---

# 27. Этапы внедрения

## Phase 1 — Audit and contracts

- изучить текущий код;
- зафиксировать pipeline;
- добавить schemas без поломки старого JSON;
- создать automated sample render 20–30 s.

## Phase 2 — Phrase grid

- beat/downbeat → bars → 8-count → 32-count;
- manual offset;
- section-to-phrase alignment;
- debug timeline.

## Phase 3 — Choreography V2

- movement library;
- phrase templates;
- candidate generation;
- scoring;
- validation;
- deterministic seed.

## Phase 4 — Visual language V2

- cue archetypes;
- mirror logic;
- lead times;
- judgment plane;
- hit feedback.

## Phase 5 — Composition and background

- safe zone;
- corridor shift;
- background profile;
- vanishing point calibration;
- road integration.

## Phase 6 — Musical visual direction

- section profiles;
- FX controller;
- camera cues;
- next-move card;
- clean/QA modes.

## Phase 7 — Editor and regeneration

- phrase editing;
- lock/regenerate;
- simplify/mirror;
- validation panel.

## Phase 8 — Full-track acceptance

- full deterministic render;
- no drift;
- choreography report;
- visual QA contact sheet;
- final clean background.

После каждой phase:

1. запускать тесты;
2. запускать short render;
3. записывать изменения в `PROGRESS.md`;
4. не переходить дальше при error-level validation issues.

---

# 28. Критерии приёмки

## Хореография

- 100% основной хореографии организовано в 8/32-count blocks;
- section changes не выглядят случайными;
- есть минимум один signature motif;
- он повторяется позже с контролируемой вариацией;
- новое движение сначала обучается;
- left/right balance проходит validation;
- нет длинной случайной цепочки одиночных cues;
- есть recovery phrases;
- прыжки и squats ограничены профилем.

## Тайминг

- рендер не дрейфует относительно музыки;
- cue достигает judgment plane в target hit_time;
- event timing воспроизводим при повторном рендере;
- manual offset работает;
- preview начинается с preroll минимум 4–8 beats.

## Визуал

- человек слева не перекрывает обязательные cues;
- road и MP4 выглядят единым пространством;
- нижняя половина не является пустой чёрной областью;
- cue понятен без угадывания по одному цвету;
- белые floor rings не используются для punch/reach;
- большие стены имеют safe opening и directional arrow;
- chorus визуально сильнее verse;
- breakdown визуально спокойнее chorus;
- FX не закрывают cues;
- финальный кадр имеет законченную композицию.

## Рабочий процесс

- старый analyzer input продолжает работать;
- пользователь может заменить audio и background без изменения кода;
- background calibration сохраняется в JSON;
- хореография редактируется по фразам;
- clean render и QA render создаются одной кнопкой;
- все ошибки показываются понятным текстом.

---

# 29. Первый обязательный deliverable Codex

Не начинать с полного трека.

Создать тестовый vertical slice длиной `30–45 s`, включающий:

1. 8 counts intro/base groove;
2. 8 counts teach step-touch;
3. 8 counts repeat;
4. 8 counts mirror;
5. 16 counts combination with punches;
6. 8 counts build;
7. 16 counts signature chorus;
8. короткий recovery.

Vertical slice должен использовать текущий MP4 background, но:

- со смещённой вправо дорожкой;
- с safe zone;
- с новым hit feedback;
- с next-move card;
- с минимум четырьмя однозначными cue archetypes;
- с QA overlay.

Показать A/B:

```text
CURRENT
vs
CHOREOGRAPHY V2 + VISUAL V2
```

Только после одобрения vertical slice выполнять полный track render.

---

# 30. Запреты

- не переписывать Analyzer GUI с нуля;
- не заменять существующий анализатор только ради модной AI-модели;
- не генерировать независимое движение на каждый beat;
- не копировать точный HUD, фон, палитру и хореографию референса;
- не использовать цвет как единственный смысл cue;
- не размещать обязательные действия в performer safe zone;
- не делать сильную камеру во время сложного движения;
- не использовать случайные FX без section/beat cue;
- не считать задачу завершённой после одного красивого скриншота;
- не рендерить полный трек до прохождения vertical slice.

---

# 31. Исследовательские принципы, на которых основано ТЗ

- В dance fitness музыка должна быть предварительно размечена как class map: секции, изменения темпа/интенсивности, recovery и кульминации.
- Fitness-хореография обычно удобнее воспринимается блоками по 8 и 32 counts.
- Человеческая синхронизация с аудио обычно точнее, чем с чисто визуальным миганием, поэтому визуал должен давать направление и предсказание, а точный ритм должен оставаться слышимым в музыке.
- Для exergame feedback полезно быть интегрированным в мир, понятным, постепенно усиливаться и использовать несколько каналов одновременно.
- Современные music-to-dance системы отдельно оценивают beat alignment, физическую правдоподобность, долгосрочную структуру, разнообразие и редактируемость; одной синхронизации нот с ударами недостаточно.

---

# 32. Финальная команда Codex

Сначала изучи репозиторий и создай `docs/CURRENT_PIPELINE_AUDIT.md`. Затем реализуй `Phase 1` и `Phase 2`, запусти тесты и создай короткий debug render. Не переходи к декоративной полировке, пока 32-count phrase planner, movement semantics, mirror logic, lead times и judgment plane не работают корректно.
