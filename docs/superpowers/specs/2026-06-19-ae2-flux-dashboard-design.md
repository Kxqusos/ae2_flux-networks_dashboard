# AE2 + Flux Networks Dashboard — Design Spec

**Дата:** 2026-06-19
**Статус:** черновик на ревью

## Цель

Веб-dashboard, через который можно:
- заказывать предметы в сети **Applied Energistics 2** (автокрафт),
- смотреть статистику энергосети **Flux Networks**,

используя компьютер **OpenComputers** внутри Minecraft как мост к игровому миру.

## Ключевое ограничение

OpenComputers (Internet Card) умеет делать только **исходящие** HTTP-запросы и **не может принимать** входящие соединения / поднимать сервер. Поэтому:

- Всё взаимодействие инициирует **client** (OC, Lua).
- **dashboard** (FastAPI) — пассивный HTTP API + хранилище + UI.
- Заказы передаются client'у не push'ом, а через **опрос** (client сам забирает очередь).

## Структура: два независимых репозитория

```
ae2_flux-networks_dashboard/   ← контейнер (не git)
├── dashboard/   ← репозиторий №1: FastAPI + фронтенд
└── client/      ← репозиторий №2: OpenComputers Lua
```

Граница между репозиториями — **контракт API** (раздел ниже). Контракт дублируется в README обоих репозиториев, чтобы части разрабатывались независимо.

## Архитектура

```
┌─────────────────────────┐         HTTPS (Bearer token)        ┌──────────────────────────┐
│  client/ (OC, Lua)      │  ── POST flux stats ───────────────▶ │  dashboard/ (FastAPI)    │
│  loop раз в 60 секунд:  │  ── POST inventory + craftables ───▶ │                          │
│  1. читает Flux         │  ── GET  pending orders ◀──────────  │  SQLite: flux_samples,   │
│  2. читает AE2          │  ── POST order result ─────────────▶ │  inventory, orders       │
│  3. забирает заказы     │                                      │                          │
│  4. requestCrafting     │                                      │  + статика (UI)          │
└─────────────────────────┘                                      └────────────┬─────────────┘
                                                          браузер (пароль) ◀───┘ polling ~5с
```

Параметры:
- Интервал опроса client → dashboard: **60 секунд** (конфигурируемо).
- История статистики Flux: почасовые снимки, окно **7 дней** (старше — удаляются).
- Доступ: dashboard в интернете. Client авторизуется **Bearer-токеном**; UI — простой пароль → сессионная кука.

---

## Контракт API (граница между репозиториями)

Все client-эндпоинты требуют заголовок `Authorization: Bearer <API_TOKEN>` (иначе `401`).
Все тела запросов/ответов — JSON.

### Client → Dashboard

#### `POST /api/client/flux`
Текущая статистика Flux Networks.
```json
{
  "energy_in": 12345,      // приход энергии за тик/секунду (ед. модпака)
  "energy_out": 9876,      // расход
  "buffer": 5000000,       // энергия в буфере сети
  "capacity": 8000000      // ёмкость буфера (опционально)
}
```
Ответ: `{"ok": true}`. Сервер обновляет `last_seen` и при необходимости пишет почасовой снимок.

#### `POST /api/client/inventory`
Срез сети AE2.
```json
{
  "items": [
    {"name": "minecraft:iron_ingot", "label": "Iron Ingot", "count": 2048}
  ],
  "craftables": [
    {"name": "minecraft:iron_ingot", "label": "Iron Ingot"}
  ]
}
```
Ответ: `{"ok": true}`. `items` — что есть в сети; `craftables` — что доступно для автокрафта.

#### `GET /api/client/orders/pending`
Заказы, ожидающие выполнения (статус `queued`).
```json
{
  "orders": [
    {"id": 42, "item": "minecraft:iron_ingot", "label": "Iron Ingot", "amount": 64}
  ]
}
```

#### `POST /api/client/orders/{id}/result`
Отчёт о ходе/итоге выполнения заказа.
```json
{
  "status": "requested",   // requested | done | failed
  "message": "craft job started"   // опционально, для failed — причина
}
```
Ответ: `{"ok": true}`. Неизвестный `id` → `404`.

### Browser (UI) → Dashboard

- `POST /api/ui/login` — `{"password": "..."}` → ставит сессионную куку.
- `GET  /api/ui/stats` — текущие значения Flux + история (почасово, до 7 дней) для графиков.
- `GET  /api/ui/items` — последний срез inventory + craftables, плюс `last_seen` / флаг «client offline».
- `POST /api/ui/orders` — `{"item": "...", "label": "...", "amount": N}` → создаёт заказ в статусе `queued`.
- `GET  /api/ui/orders` — список заказов со статусами.

UI-эндпоинты требуют валидную сессионную куку (кроме `login`).

### Жизненный цикл заказа

```
queued  ──(client забрал, вызвал requestCrafting)──▶  requested
requested  ──(джоба завершилась успешно)──▶  done
requested  ──(ошибка / нельзя скрафтить)──▶  failed
```

Все переходы после `queued` репортит **client** через `POST /api/client/orders/{id}/result` (т.к. dashboard не может достучаться до client).

---

## dashboard/ (FastAPI + фронтенд)

```
dashboard/
├── app/
│   ├── main.py          # приложение, подключение роутеров, раздача static
│   ├── config.py        # env: API_TOKEN, UI_PASSWORD, DB_PATH, POLL_*, RETENTION_DAYS=7
│   ├── db.py            # SQLite: схема, подключение, миграция при старте
│   ├── auth.py          # Bearer-токен для client; пароль+кука для UI
│   ├── models.py        # pydantic-схемы payload'ов
│   ├── store.py         # бизнес-логика: запись снимков, очистка, очередь заказов
│   └── routers/
│       ├── client.py    # /api/client/*
│       └── ui.py        # /api/ui/*
├── app/static/          # index.html, app.js, styles.css (Chart.js c CDN)
├── tests/               # pytest + FastAPI TestClient
├── docs/                # эта спека
├── requirements.txt
└── README.md            # запуск + копия контракта API
```

### Таблицы SQLite

- `flux_samples(id, ts, energy_in, energy_out, buffer, capacity)` — почасовые снимки. Снимок пишется, если для текущего часового бакета его ещё нет. Очистка строк старше 7 дней.
- `inventory(id=1, ts, items_json, craftables_json)` — единственная строка с последним срезом; `ts` = `last_seen`.
- `orders(id, item, label, amount, status, message, created_at, updated_at)`.

### Почасовой снимок

Client шлёт Flux раз в минуту → сервер всегда держит «текущее» значение в `inventory`/памяти для UI, но в `flux_samples` пишет максимум одну строку в час (по часовому бакету `ts`). Это даёт ~168 точек за неделю для графиков.

### Frontend

Vanilla JS + Chart.js (CDN), без сборки. Две панели:
- **Статистика:** текущая мощность in/out, буфер/ёмкость, линейные графики энергии за неделю.
- **Заказы:** поиск по `craftables`, ввод количества, кнопка «Заказать», список заказов со статусами, индикатор «client offline».

Браузер опрашивает `/api/ui/stats` и `/api/ui/items` каждые ~5 секунд.

## client/ (OpenComputers, Lua)

```
client/
├── main.lua        # конфиг + главный цикл (pcall на каждой итерации)
├── config.lua      # DASHBOARD_URL, API_TOKEN, POLL_INTERVAL=60
├── ae2.lua         # обёртка me_controller: getItemsInNetwork, getCraftables, request(n)
├── flux.lua        # обёртка компонента Flux Networks: чтение энергостатистики
├── http.lua        # internet-карта: JSON + заголовок авторизации + обработка ошибок
├── json.lua        # библиотека JSON (вендоринг)
└── README.md       # установка в игре + копия контракта API
```

Игровые требования: Internet Card; Adapter рядом с ME-контроллером AE2; доступ к компоненту Flux Networks (Adapter рядом с Flux-контроллером).

Главный цикл (раз в 60с), вся итерация в `pcall`:
1. прочитать Flux → `POST /api/client/flux`;
2. прочитать AE2 (items + craftables) → `POST /api/client/inventory`;
3. `GET /api/client/orders/pending`; для каждого: найти craftable, вызвать `request(amount)`, отчитаться `requested`; при ошибке — `failed`;
4. (по возможности) проверить статус ранее запущенных джоб и отчитаться `done`/`failed`.

## Обработка ошибок

- **Client:** каждая итерация в `pcall` — цикл не падает; при сетевой ошибке лог + повтор на следующей итерации; экспоненциальный бэкофф при серии неудач.
- **Dashboard:** валидация payload через pydantic (`422` на мусор); `401` на плохой токен; UI помечает «client offline», если `last_seen` старше ~2 минут.

## Тестирование

- **Dashboard (pytest + TestClient):** авторизация (Bearer/кука), все эндпоинты, жизненный цикл заказа (`queued→requested→done/failed`), логика почасового снимка и очистки >7 дней. SQLite во временном файле.
- **Client (busted + моки OC-компонентов):** сборка payload'ов, обработка очереди заказов и переходов статусов, расчёт интервала/бэкоффа. Чистая логика отделена от обращений к компонентам.

## Открытые вопросы / проверить в игре

- Точные имена методов компонента **Flux Networks** в OpenComputers зависят от версии модпака — сверить в игре. Изоляция в `flux.lua`.
- Точные имена методов AE2-компонента (`me_controller` vs `me_interface`) и сигнатура `craftable.request` — сверить под версию AE2/OC модпака. Изоляция в `ae2.lua`.

## Вне области (YAGNI)

- Множественные пользователи / роли — только один пароль на UI.
- Управление паттернами/процессорами AE2 из UI.
- Real-time websockets — достаточно polling'а.
- Графики по отдельным предметам — только агрегированная энергия Flux.
