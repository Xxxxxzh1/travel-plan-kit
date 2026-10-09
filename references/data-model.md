# The `trip.yaml` data model

Every output is generated from one file. This documents each field.

The shape below is complete; most fields are optional. `trip.example.yaml` at the
repo root is a minimal commented template, and
`examples/italy-switzerland/trip.yaml` is a full worked example.

## Authoring markup

Text fields accept exactly two markers. Nothing else is interpreted, and
everything else is HTML-escaped — user text is never trusted as markup.

| Write | You get | Use for |
|---|---|---|
| `**text**` | a highlighted span, tinted with the day's country colour | museum names, emphasised times |
| `!!text!!` | an amber attention span (Markdown output renders it as `**⚠ text**`) | "not booked", "leave early" |

`<br>` is the one HTML tag allowed, for line breaks inside a note. Newlines in
YAML block scalars are **not** converted — use `<br>`.

## `meta` — required

```yaml
meta:
  title: Italy & Switzerland     # Latin-script title (used in PDF/HTML headers)
  title_zh: 意大利 · 瑞士          # primary-language title (used everywhere else)
  slug: italy-switzerland        # short identifier
  emoji: "🇮🇹🇨🇭"                 # split into leading/trailing flags in the roadbook title
  start: 2027-09-24              # ISO date, required
  end: 2027-10-07                # ISO date, required
  travelers: [Janz, Lynn]        # shown in headers; also drives "2 travellers" wording
  route: [罗马, 那不勒斯, 佛罗伦萨]  # roadbook header breadcrumb
  countries:                     # country-code -> display name, for the filter chips
    it: 意大利
    ch: 瑞士
  departure_note: "10/7 苏黎世 15:30 起飞"   # optional; shown on the final day's card
```

`start`/`end` are validated: every day must fall inside the range, and days must
be in ascending date order.

## `summary` — the one-glance block

This is what a border officer or a hotel reads first, so keep it factual.

```yaml
summary:
  entry:  {date: 2027-09-24, place: Rome Fiumicino (FCO), Italy, time: "20:05", flight: EK95}
  exit:   {date: 2027-10-07, place: Zurich (ZRH), Switzerland, time: "15:30", flight: EK88}
  countries: "Italy (9 nights) · Switzerland (4 nights)"
  transport_modes: International flights (via Dubai) · High-speed & regional trains
  status: All flights, train tickets and accommodation are fully paid and confirmed.
```

Prefer **nights** over **days** for country totals. A day that spans a border —
fly out of Zurich, arrive in Dubai — is genuinely two countries, and counting
days double-counts it.

## `hero` — roadbook header overrides

```yaml
hero:
  who:   ["👤 Janz & Lynn", "✅ 全部出票"]
  stats: ["🗓 14 天 13 晚", "🚄 9 段列车"]
  meta:  "2027.09.24 — 10.07 · 罗马 → 那不勒斯 → …"    # optional; overrides the derived breadcrumb
```

All optional. Without `stats`, the day count and the number of rail legs are
derived. Without `meta`, the breadcrumb is derived from `meta.route`.

## `flights`

```yaml
flights:
  - {date: 2027-09-24, code: EK311, from: "Hangzhou Xiaoshan (HGH)", to: "Dubai (DXB)", dep: "00:10", arr: "04:30"}
```

Used by the itinerary header and available to templates. The same flights will
normally also appear as `transport` entries on their day, described in more
detail — that duplication is intentional, because one is a summary line and the
other is the day's schedule.

## `lodging` — declared once, referenced by id

```yaml
lodging:
  - id: rome                     # required, unique; referenced from days
    city: 罗马                    # required, primary language
    city_en: Rome                # optional; used to qualify the map query
    country: IT
    type: 民宿                    # primary language, e.g. 民宿 / 酒店
    type_en: Private apartment   # used by the generated sample tickets
    platform: Airbnb
    host: Marco                  # omit for a hotel
    address: Via dei Fiori, 12, Rome, Italy    # required
    map_query: Via dei Fiori, 12, Rome, Italy  # optional; defaults to address + city
    checkin:  {date: 2027-09-24, time: "16:00"}
    checkout: {date: 2027-09-27, time: "10:00"}
    nights: 3                    # validated against the dates
    phone: "+41 79 000 00 00"    # optional
    note: 不可退款                # optional, shown in the stay box
    tickets: [stay-rome]         # optional back-reference, used by the sample-ticket generator
```

**Why ids and not inlined objects.** A three-night stay is referenced by three
days. Inlining it means the address, the host and the check-in time each exist
in three places, and every correction has to be made three times. The generator
emits the stay once and the renderer looks it up.

`_name` (e.g. `罗马民宿 · 房东 Marco`) is built for you from `city` + `type` +
`host`; do not write it yourself.

`map_query` deliberately includes the city. A bare street name geocodes to the
wrong country far more often than you would expect.

`nights` is cross-checked against `checkin`/`checkout` and the build fails if
they disagree.

## `days` — the itinerary

```yaml
days:
  - n: 1                         # display number; defaults to position
    date: 2027-09-24             # required
    city: 罗马                    # required; may contain " → " for travel days
    country: IT                  # drives the row colour and the filter chips
    weather: {temp: "18–26°C", wear: 轻薄长袖 + 薄外套, cold: false}
    slots:
      - {key: 夜, icon: "🛬", text: 20:05 抵达罗马 FCO → 入市区 → 入住}
    transport:
      - {icon: "🚄", title: Italo 9975, sub: 罗马 Termini **12:41** → 那不勒斯 **13:58**,
         meta: 6 车厢 座 5/6, badge: 已购}
    lodging: rome                                  # id reference, or omit on a departure day
    tickets: {transport: [italo], scenic: [], stay: [stay-rome]}
```

| Field | Notes |
|---|---|
| `weather.cold` | `true` renders a red freeze chip (used for high-altitude days) |
| `slots[].key` | the time-of-day label in the narrow column: 上午 / 下午 / 晚 / 全天 / … |
| `slots[].icon` | one emoji, shown in the roadbook drawer |
| `transport[].sub` | the route and times — this is the line that matters |
| `transport[].badge` | `已购` (green), `现场` (amber), `补票` (red). Anything else falls back to green |
| `tickets` | the three keys are fixed: `transport`, `scenic`, `stay` |

A day with no `lodging` renders as a departure day, using `meta.departure_note`.

## `tickets` — id, label, file

```yaml
tickets:
  - {id: italo, category: transport, label: Italo 9975 罗马 → 那不勒斯, file: tickets/train-italo.png}
  - {id: milano-spiez, category: transport, label: 米兰 → 施皮茨（REG + RE 换乘）,
     files: [tickets/train-milano-spiez-p1.png, tickets/train-milano-spiez-p2.png]}
```

- `category` must be one of `transport`, `scenic`, `stay`. It decides which
  drawer tab the ticket appears under.
- `file` for a single-page ticket, `files` for a multi-page one. Multi-page
  tickets get `· 第 N 页` appended to each page's caption automatically.
- Paths are relative to the directory containing `trip.yaml`. A missing file is
  a build error, reported with the ticket id.

Keep `label` short — it is the caption under the thumbnail and the title in the
lightbox.

## `notes` — reminders

```yaml
notes:
  - {level: red,  text: "**登顶段未预订**<br>需现场补票"}
  - {level: warn, text: "**早退房赶车**：10/1 列车 09:38 发"}
  - {level: todo, text: 确认蒸汽小火车 10 月运营时刻}
```

| `level` | Renders as |
|---|---|
| `red` | a red-barred alert |
| `warn` | an amber-barred alert |
| `""` (or omitted) | a neutral note, grouped with the alerts |
| `todo` | a checklist item in the "行前 To-Do" section |

## `footer`

A single line of provenance, shown at the bottom of every document. `<br>` works.
