# ANALYSIS.md

> Актуально на 01.11.2026, ветка `opencode-agent`.
>
> Документ описывает **текущее состояние** приложения «Investing Demo»: назначение,
> стек, архитектуру, модель данных, сценарии работы и восстановленные
> функциональные требования. История исправлений и аудит зависимостей вынесены в
> `AUDIT.md`, исходные требования — в `REQUIREMENTS.md`, новая функциональность —
> в `NEW_FEATURE.md`.

## 1. Назначение приложения и возможности

**Назначение.** «Investing Demo» — учебное Django-приложение для просмотра
акций, работы со справочником инструментов и анализа накопленной истории
рыночных цен. Рыночные данные поступают из Tinkoff Invest API, фоновая задача
Celery периодически обновляет последние цены и сохраняет снимки в базу.

Приложение поддерживает три роли:

| Роль | Возможности |
|---|---|
| Анонимный пользователь | Просмотр списка акций, карточки акции, истории цен, чтение REST API |
| Аутентифицированный пользователь | Всё вышеперечисленное, а также создание, редактирование и удаление акций через HTML-формы |
| Администратор | Управление акциями и снимками цен в Django Admin |

**Реализованные возможности:**

- список акций с текущей ценой, валютой и цветовой индикацией роста/падения
  (`dashboard/views.py:ShareListView`, `dashboard/templates/dashboard/list.html`);
- карточка акции с текущей ценой, временем обновления и графиком Tinkoff за
  180 дней (`dashboard/views.py:ShareDetailView`,
  `dashboard/services/graph.py:get_graph`);
- история рыночных цен, накопленная в базе: периоды 7/30/90/180/365 дней,
  статистика, абсолютное и процентное изменение, график и последние снимки
  (`dashboard/views.py:ShareHistoryView`,
  `dashboard/services/price_history.py`);
- регистрация, вход и выход пользователя
  (`user/urls.py`, `user/views.py`, `user/forms.py`);
- создание, редактирование и удаление акций через HTML-формы только для
  аутентифицированных пользователей (`dashboard/views.py`);
- CRUD REST API по акциям с пагинацией, фильтрацией, сортировкой и поиском
  (`dashboard/api/v1/`);
- периодическое обновление цен и запись снимков в историю задачей Celery
  (`dashboard/tasks.py:update_last_price`, `config/celery.py`);
- импорт справочника акций management-командой
  (`dashboard/management/commands/add_shares.py`);
- администрирование акций и истории цен (`dashboard/admin.py`);
- логирование внешних интеграций и фоновых задач в консоль и файл
  (`config/settings.py:LOGGING`).

**Основные маршруты:**

| Метод и URL | Назначение | Доступ |
|---|---|---|
| `GET /` | Список акций | Анонимно |
| `GET /<pk>` | Карточка акции и график Tinkoff | Анонимно |
| `GET /history/<pk>?days=30` | История накопленных цен | Анонимно |
| `GET/POST /create` | Создание акции | Только вход |
| `GET/POST /update/<pk>` | Редактирование акции | Только вход |
| `GET/POST /delete/<pk>` | Подтверждение и удаление акции | Только вход |
| `GET /api/v1/` | Корень REST API | По настройке |
| `GET/POST /api/v1/shares/` | Список и создание акций | По настройке |
| `GET/PUT/PATCH/DELETE /api/v1/shares/<pk>/` | Операции с одной акцией | По настройке |
| `GET/POST /user/login/` | Вход | Анонимно |
| `GET/POST /user/registration/` | Регистрация | Анонимно |
| `POST /user/logout/` | Выход | Только вход |
| `GET /admin/` | Django Admin | Администратор |

## 2. Технологический стек и зависимости

| Слой | Технология | Где используется |
|---|---|---|
| Язык и фреймворк | Python 3.12+ (проверено на 3.14.4), Django 6.1.2 | `manage.py`, `config/settings.py` |
| База данных | SQLite по умолчанию; PostgreSQL 17 через `DB_ENGINE=postgres` | `config/settings.py:build_database_config`, `docker-compose.yml` |
| Драйвер PostgreSQL | `psycopg[binary]` 3.3.6 | `requirements.txt` |
| REST API | Django REST Framework 3.18.3, django-filter 26.2 | `dashboard/api/v1/` |
| HTML-формы | django-crispy-forms 2.7, crispy-bootstrap5 2026.9, Bootstrap 5 | `dashboard/templates/`, `user/templates/` |
| Графики | plotly 7.1.0 (серверная генерация HTML), plotly.js через CDN | `dashboard/services/graph.py`, `dashboard/services/price_history.py` |
| Внешний API | Tinkoff Invest SDK (опционально, git-коммит) | `dashboard/services/market_data.py` |
| Асинхронные задачи | Celery 5.6.3, Redis 6.4.0 (клиент) | `config/celery.py`, `dashboard/tasks.py` |
| Конфигурация | python-dotenv 1.2.4, переменные окружения | `config/settings.py`, `.env.example` |
| Инфраструктура | Docker Compose: PostgreSQL 17, Redis 8 | `docker-compose.yml` |
| Разработка | coverage 7.17.0, ruff 0.17.3 | `requirements-dev.txt`, `pyproject.toml` |

**Прямые runtime-зависимости** (`requirements.txt`):

```text
Django==6.1.2
djangorestframework==3.18.3
django-filter==26.2
django-crispy-forms==2.7
crispy-bootstrap5==2026.9
celery[redis]==5.6.3
psycopg[binary]==3.3.6
plotly==7.1.0
python-dotenv==1.2.4
```

**Опциональные зависимости** (`requirements-optional.txt`): `grpcio`,
`protobuf`, `cachetools`, `deprecation`, `python-dateutil`. Сам Tinkoff SDK
устанавливается отдельно из официального репозитория, поскольку пакет
недоступен на PyPI:

```bash
pip install -r requirements-optional.txt
pip install --no-deps "git+https://github.com/RussianInvestments/invest-python.git@fcf0af1e27f053cd4bc75eb20863ece23a202d47"
```

Без SDK и без `TINKOFF_TOKEN` приложение запускается: страницы открываются,
история читается из базы, а рыночные данные деградируют предсказуемо.

**Значения по умолчанию** (`config/settings.py`):

- `DEBUG=True`, `LANGUAGE_CODE=ru-ru`, `TIME_ZONE=Europe/Moscow`;
- SQLite `db.sqlite3`, если не задан `DB_ENGINE=postgres`;
- `ALLOWED_HOSTS=localhost,127.0.0.1,[::1]`;
- `LOGIN_URL=user:auth`, успешный вход и выход ведут на `dashboard:index`;
- брокер Celery — `redis://127.0.0.1:6379/0`;
- API открыт по умолчанию; `API_REQUIRE_AUTH=true` включает
  `IsAuthenticatedOrReadOnly`;
- production-настройки безопасности применяются только при `DEBUG=false`,
  причём без `DJANGO_SECRET_KEY` приложение завершается с
  `ImproperlyConfigured`.

## 3. Структура проекта

```text
.
├── manage.py                     # точка входа Django
├── requirements.txt              # runtime-зависимости
├── requirements-dev.txt          # coverage, ruff
├── requirements-optional.txt     # зависимости Tinkoff SDK
├── pyproject.toml                # настройки ruff
├── .env.example                  # пример конфигурации
├── docker-compose.yml            # PostgreSQL и Redis
├── README.md                     # запуск и использование
├── REQUIREMENTS.md               # восстановленные требования и дефекты
├── AUDIT.md                      # аудит, исправления, ограничения
├── NEW_FEATURE.md                # требования и реализация истории цен
├── ANALYSIS.md                   # этот документ
├── config/                       # проект
│   ├── settings.py               # настройки из окружения
│   ├── urls.py                   # корневая маршрутизация
│   ├── celery.py                 # Celery и расписание Beat
│   ├── __init__.py               # экспорт celery_app
│   └── wsgi.py / asgi.py         # точки входа
├── dashboard/                    # приложение «акции»
│   ├── models.py                 # Share, PriceHistory
│   ├── views.py                  # список, карточка, история, CRUD
│   ├── forms.py                  # ShareModelForm
│   ├── urls.py                   # HTML- и API-маршруты
│   ├── admin.py                  # ShareAdmin, PriceHistoryAdmin
│   ├── tasks.py                  # update_last_price
│   ├── api/                      # REST API
│   │   ├── urls.py
│   │   └── v1/
│   │       ├── urls.py
│   │       ├── router.py         # DefaultRouter, shares
│   │       ├── views.py          # ShareViewSet, ShareFilter
│   │       └── serializer.py     # ShareSerializer
│   ├── services/
│   │   ├── market_data.py        # Tinkoff: цены, котировки, тренд
│   │   ├── graph.py              # график Tinkoff за 180 дней
│   │   └── price_history.py      # периоды, статистика, график истории
│   ├── management/commands/
│   │   └── add_shares.py         # импорт справочника
│   ├── migrations/               # 0001…0009
│   ├── templates/dashboard/      # base, list, detail, history, create, delete
│   ├── static/dashboard/css/     # Bootstrap и стили
│   ├── tests.py                  # модели, HTML, API, задача
│   ├── tests_services.py         # сервисы и команда импорта
│   └── tests_history.py          # история цен
└── user/                         # пользователи
    ├── models.py                 # User = get_user_model()
    ├── forms.py                  # RegistrationForm, EmailAuthenticationForm
    ├── views.py                  # RegistrationView
    ├── urls.py                   # login, registration, logout
    ├── tests.py                  # регистрация, вход, выход
    ├── templates/user/           # base, auth, registration
    └── static/user/css/          # стили страниц входа
```

Собственной модели пользователя нет: `user/models.py` содержит
`User = get_user_model()` и использует стандартную
`django.contrib.auth.models.User`. Каталог `user/migrations` не содержит
миграций приложения.

## 4. Архитектура и взаимодействие компонентов

Приложение построено по классической Django-архитектуре MVT с выделенным
сервисным слоем, отдельным REST-слоем и фоновой обработкой через Celery.

### 4.1 Слои

1. **Конфигурация проекта.** `config/settings.py` читает переменные окружения
   и `.env`, задаёт БД, DRF, Celery, логирование, безопасность и токен Tinkoff.
   `config/urls.py` выполняет корневую маршрутизацию, `config/wsgi.py` и
   `config/asgi.py` — точки входа.
2. **Маршрутизация.** `config/urls.py` подключает `dashboard.urls` по корню и
   `user.urls` по префиксу `user/`. API дополнительно проходит через
   `dashboard/api/urls.py` → `dashboard/api/v1/urls.py` →
   `dashboard/api/v1/router.py`.
3. **HTML-представления.** `dashboard/views.py` использует generic views:
   `ShareListView`, `ShareDetailView`, `ShareHistoryView` доступны анонимно;
   `ShareCreateView`, `ShareUpdateView`, `ShareDeleteView` защищены
   `LoginRequiredMixin`. Пользовательские страницы построены на встроенных
   `LoginView`/`LogoutView` и `RegistrationView` (`FormView`).
4. **Формы и валидация.** `dashboard/forms.py:ShareModelForm` включает все поля
   `Share`. `user/forms.py:RegistrationForm` проверяет совпадение паролей,
   регистронезависимую уникальность e-mail и вызывает `validate_password`.
   `EmailAuthenticationForm` принимает e-mail вместо username и нормализует его
   к нижнему регистру.
5. **Сервисный слой.** `dashboard/services/market_data.py` инкапсулирует
   Tinkoff SDK, лениво импортирует его, преобразует `Quotation` в `Decimal` и
   рассчитывает тренд. `dashboard/services/graph.py` строит график дневных
   свечей Tinkoff. `dashboard/services/price_history.py` работает только с
   накопленными в БД снимками: выбирает период, считает статистику, прореживает
   ряд и строит график.
6. **Слой данных.** `dashboard/models.py` содержит `Share` и `PriceHistory`;
   доступ — через Django ORM. Схема управляется миграциями `0001…0009`.
7. **REST-слой.** `ShareViewSet` (`ModelViewSet`) использует `ShareSerializer`,
   `ShareFilter`, `OrderingFilter` и `SearchFilter`. Пагинация —
   `LimitOffsetPagination`, 100 записей. При `COERCE_DECIMAL_TO_STRING=False`
   цена передаётся в JSON числом.
8. **Фоновые задачи.** `config/celery.py` создаёт приложение `Celery("config")`,
   читает настройки с префиксом `CELERY`, включает `autodiscover_tasks()` и
   задаёт расписание `update-share-prices-every-5-minutes` с интервалом
   300 секунд. `config/__init__.py` реэкспортирует `celery_app`.
9. **Интеграция с внешним рынком.** Celery Beat → Redis → Celery Worker →
   `update_last_price` → `get_last_data` → Tinkoff Invest API (gRPC).
10. **Администрирование и логирование.** `ShareAdmin` и `PriceHistoryAdmin`
    зарегистрированы в Django Admin. Логгер `main` пишет в консоль и в файл
    `app.logs` (путь можно переопределить через `DJANGO_LOG_FILE`).

### 4.2 Схема взаимодействия

```text
Браузер / API-клиент
        │ HTTP
        ▼
config/urls.py
   ├── dashboard/urls.py ──> View / ViewSet ──> Form / Serializer
   │                              │
   │                              ├── services/graph.py ──gRPC──> Tinkoff API
   │                              ├── services/price_history.py ──> ORM
   │                              └── ORM ──> SQLite / PostgreSQL
   ├── user/urls.py ──> LoginView / RegistrationView / LogoutView ──> ORM
   └── admin/ ──> Django Admin ──> ORM

Celery Beat ──> Redis ──> Celery Worker
                              └── tasks.update_last_price
                                    ├── services/market_data.py ──gRPC──> Tinkoff API
                                    ├── ORM: Share
                                    └── ORM: PriceHistory
```

Важно: HTML-представления не запускают Celery. Цены обновляются только по
расписанию Beat (или вручную при вызове задачи), а страница истории читает
только базу и не делает запросов в Tinkoff.

### 4.3 Ключевые архитектурные решения

- **SQLite по умолчанию, PostgreSQL опционально.** Локальный запуск не требует
  Docker; для PostgreSQL достаточно `DB_ENGINE=postgres` и переменных
  `POSTGRES_*`.
- **Decimal вместо Float.** `Share.last_price` и `PriceHistory.price` имеют тип
  `DecimalField(max_digits=20, decimal_places=9)`, что сохраняет точность
  котировок Tinkoff (units + nano).
- **Изоляция внешнего API.** Tinkoff SDK импортируется лениво; отсутствие
  токена или пакета не мешает запуску приложения. Ошибки графики и фоновой
  задачи обрабатываются и логируются.
- **История цен в БД.** Новые снимки накапливаются при обновлении цен и не
  требуют отдельного внешнего запроса при просмотре. Дубли исключаются
  ограничением `UNIQUE(share, quoted_at)`.
- **Совместимость API.** По умолчанию API остаётся открытым, как в исходной
  версии; ужесточение доступа включается настройкой `API_REQUIRE_AUTH`.

## 5. Модель данных

### 5.1 Сущность `Share` («Акция»)

Определена в `dashboard/models.py:Share`, таблица `dashboard_share`.

| Поле | Тип | Ограничения / особенности |
|---|---|---|
| `id` | `BigAutoField` | Первичный ключ |
| `figi` | `CharField(255)` | `unique=True`, обязательное |
| `isin` | `CharField(255)` | Обязательное, без уникальности |
| `name` | `CharField(255)` | Обязательное, `verbose_name="Наименование компании"` |
| `ticker` | `CharField(10)` | `unique=True`, `verbose_name="Тикер"` |
| `currency` | `CharField(20)` | Обязательное, `verbose_name="Валюта"` |
| `uid` | `CharField(255)` | `unique=True`, обязательное |
| `last_price` | `DecimalField(20, 9)` | `null=True`, `blank=True`, `verbose_name="Текущая цена"` |
| `is_trend_high` | `BooleanField` | `null=True`, `blank=True`, `verbose_name="Растет цена"` |
| `updated_at` | `DateTimeField` | `auto_now=True`, `null=True`, `blank=True` |

Метаданные: `verbose_name="Акция"`, `verbose_name_plural="Акции"`.
Строковое представление: `"<ticker> — <name>"`.

### 5.2 Сущность `PriceHistory` («Снимок цены»)

Определена в `dashboard/models.py:PriceHistory`, таблица
`dashboard_pricehistory`. Хранит накопленную историю рыночных цен.

| Поле | Тип | Ограничения / особенности |
|---|---|---|
| `id` | `BigAutoField` | Первичный ключ |
| `share` | `ForeignKey(Share)` | `on_delete=CASCADE`, `related_name="price_history"` |
| `price` | `DecimalField(20, 9)` | Цена снимка без потери точности |
| `quoted_at` | `DateTimeField` | Время котировки, полученное от API |
| `created_at` | `DateTimeField` | `auto_now_add=True`, время записи в БД |

Метаданные: `verbose_name="Снимок цены"`, `verbose_name_plural="История цен"`,
сортировка по умолчанию `-quoted_at`. Ограничение
`UniqueConstraint(fields=["share", "quoted_at"], name="unique_share_price_quoted_at")`
исключает дублирование одного и того же события на уровне БД.

### 5.3 Сущность `User` («Пользователь»)

Собственной модели нет. Используется стандартная
`django.contrib.auth.models.User` со стандартными полями (`username`,
`password`, `email`, `first_name`, `last_name`, `is_staff`, `is_active`,
`is_superuser`, `date_joined`, `last_login`).

Особенности использования:

- при регистрации e-mail приводится к нижнему регистру и сохраняется
  одновременно в `username` и `email`
  (`user/forms.py:RegistrationForm.save`);
- уникальность проверяется регистронезависимо по `username` и `email`
  (`user/forms.py:RegistrationForm.clean`);
- вход выполняется по e-mail: поле `username` формы принимает e-mail и
  нормализует его (`user/forms.py:EmailAuthenticationForm`);
- пароль проверяется настроенными `AUTH_PASSWORD_VALIDATORS` через
  `validate_password`.

### 5.4 Связи и ER-модель

```text
Share 1 ──────── N PriceHistory
  │                   │
  │ FK не связан      │ share_id → Share.id
  │ с User            │ ON DELETE CASCADE
  ▼                   ▼
auth_user (стандартная модель Django)

Служебные таблицы: django_session, django_admin_log,
django_content_type, django_migrations, auth_*.
```

- `Share` **не связан** с `User`: справочник акций общий, право на изменение
  определяется только фактом аутентификации.
- `PriceHistory` связан с `Share` отношением «один ко многим»; при удалении
  акции её история удаляется каскадно.
- Логическая связь «акция ↔ внешние рыночные данные» реализуется по
  `Share.figi` при вызовах Tinkoff API, а не отдельной таблицей.

### 5.5 Жизненный цикл данных

1. **Импорт справочника.** `add_shares` получает инструменты из Tinkoff и
   выполняет `update_or_create(figi=...)`: существующая запись обновляется,
   новая создаётся.
2. **Обновление цены.** `update_last_price` для каждой акции получает цену и
   время котировки, обновляет `last_price`, `is_trend_high` и `updated_at`,
   затем создаёт снимок `PriceHistory`.
3. **Просмотр истории.** Страница `/history/<pk>` выбирает снимки за период из
   БД, считает статистику, строит график и показывает последние 20 записей.
4. **Удаление акции.** Удаление `Share` каскадно удаляет связанные
   `PriceHistory`.
5. **Срок хранения.** Ограничения по сроку хранения снимков нет; очистка при
   необходимости может быть добавлена отдельной периодической задачей.

### 5.6 Миграции

| Миграция | Изменение |
|---|---|
| `0001_add_share.py` | Создание модели `Share` |
| `0002_update_share.py` | Обновление полей `Share` |
| `0003_add_uuid.py` | Добавление `uid` |
| `0004_add_last_price.py` | Добавление `last_price` и `is_trend_high` |
| `0005_add_verbose_name.py` | Русские `verbose_name` |
| `0006_add_verbose_name.py` | Русские `verbose_name` |
| `0007_add_updated_at.py` | Добавление `updated_at` |
| `0008_decimal_last_price.py` | Замена `FloatField` на `DecimalField(20, 9)` |
| `0009_pricehistory.py` | Создание `PriceHistory` и ограничения уникальности |

## 6. Путь HTTP-запроса и сценарии

### 6.1 Общая цепочка

1. `manage.py` устанавливает `DJANGO_SETTINGS_MODULE=config.settings`.
2. WSGI/ASGI-обработчик читает `ROOT_URLCONF = "config.urls"`.
3. Запрос проходит middleware: Security → Session → Common → CSRF →
   Authentication → Messages → XFrameOptions. `AuthenticationMiddleware`
   заполняет `request.user`.
4. `config/urls.py` направляет запрос в `dashboard.urls`, `user.urls` или
   Django Admin.
5. Представление или ViewSet обращается к формам, сериализаторам, сервисам и
   ORM, после чего возвращает HTML-ответ или JSON.

### 6.2 Сценарий A — список акций `GET /`

1. `dashboard/urls.py` → `ShareListView`.
2. `ListView` формирует `Share.objects.all().order_by("name")` и применяет
   `Paginator` с `paginate_by = 100`.
3. ORM выполняет `SELECT ... FROM dashboard_share ORDER BY name LIMIT 100`.
4. Шаблон `list.html` выводит тикер-ссылку, название, ISIN и цену с валютой.
   Для акций с ценой ячейка подсвечивается зелёным при `is_trend_high=True` и
   розовым иначе; для акций без цены выводится «—» без подсветки.
5. Анонимный пользователь не видит кнопку «Добавить» и колонку «Управление».

### 6.3 Сценарий B — карточка акции `GET /<pk>`

1. `ShareDetailView` загружает акцию по `id`; для отсутствующего `pk` возвращается
   штатный 404.
2. `get_context_data` вызывает `get_graph(share)`.
3. `get_graph` открывает Tinkoff-клиент, запрашивает дневные свечи за 180 дней и
   строит HTML-фрагмент plotly.
4. При отсутствии токена, пакета, данных или ошибке API сервис логирует
   предупреждение и возвращает `None`; шаблон показывает сообщение
   «График недоступен», а страница остаётся работоспособной.
5. На странице отображаются название, тикер, текущая цена, время обновления,
   кнопка «История цен» и график Tinkoff.

### 6.4 Сценарий C — история цен `GET /history/<pk>?days=<N>`

1. `ShareHistoryView` загружает акцию; для отсутствующего `pk` — 404.
2. `get_period_days` принимает только 7, 30, 90, 180 или 365 дней. При
   отсутствующем или недопустимом значении используется 30 дней.
3. `get_history` выбирает `PriceHistory` за последние `days` дней, сортируя от
   старых к новым.
4. `calculate_statistics` считает количество точек, первую/последнюю/
   минимальную/максимальную цену, абсолютное изменение и процент к первой цене.
   Если первая цена равна нулю, процент не рассчитывается.
5. `build_history_graph` прореживает ряд (`MAX_GRAPH_POINTS=500`), сохраняя
   первую и последнюю точки, и строит график plotly по данным БД.
6. В контекст передаются последние 20 снимков; при отсутствии данных шаблон
   показывает понятное пустое состояние.

### 6.5 Сценарий D — создание, редактирование и удаление

- `GET/POST /create` → `ShareCreateView` (`ShareFormMixin` + `CreateView`).
  Форма содержит все поля `Share`; после сохранения — редирект на список.
- `GET/POST /update/<pk>` → `ShareUpdateView` (`ShareFormMixin` + `UpdateView`).
  Форма заполняется текущими значениями; после сохранения — редирект на список.
- `GET/POST /delete/<pk>` → `ShareDeleteView` (`LoginRequiredMixin` +
  `DeleteView`). GET показывает подтверждение с названием акции, POST удаляет
  запись и перенаправляет на список.
- Все три представления требуют аутентификации. При её отсутствии
  `LoginRequiredMixin` перенаправляет на `/user/login/?next=<исходный URL>`.

### 6.6 Сценарий E — REST API

1. `GET /api/v1/` формируется `DefaultRouter`.
2. `GET /api/v1/shares/` → `ShareViewSet.list` → `Share.objects.all()` →
   фильтры (`name`, `ticker`), сортировка (`ordering` по `name`/`ticker`),
   поиск по префиксу `name` (`search`) → пагинация `limit`/`offset` по 100.
3. `ShareSerializer` отдаёт поля `id`, `figi`, `isin`, `name`, `ticker`,
   `currency`, `uid`, `last_price`, `is_trend_high`, `updated_at`.
4. `POST`, `PUT`, `PATCH`, `DELETE` обрабатываются `ModelViewSet`;
   `uid` необязателен: при создании генерируется UUID, при обновлении без
   `uid` сохраняется прежнее значение.
5. По умолчанию API открыт. При `API_REQUIRE_AUTH=true` действует
   `IsAuthenticatedOrReadOnly`: чтение остаётся открытым, запись требует
   аутентификации.

### 6.7 Сценарий F — аутентификация

1. `GET/POST /user/login/` → встроенный `LoginView` с
   `EmailAuthenticationForm`; при успехе создаётся сессия и выполняется
   редирект на `next` или на список акций. Уже вошедший пользователь
   перенаправляется автоматически.
2. `GET/POST /user/registration/` → `RegistrationView` (`FormView`).
   `RegistrationForm` проверяет пароли, уникальность e-mail и сложность пароля;
   при успехе пользователь создаётся, выполняется `login`, затем редирект на
   список акций.
3. `POST /user/logout/` → встроенный `LogoutView`; сессия завершается, затем
   редирект на список. GET-запрос возвращает 405.
4. В шапке сайта отображаются e-mail пользователя и POST-форма «Выход» либо
   кнопка «Войти» для анонимного пользователя.

### 6.8 Сценарий G — фоновое обновление цен

1. Celery Beat каждые 5 минут публикует задачу
   `dashboard.tasks.update_last_price`.
2. Worker перебирает все `Share`.
3. Для каждой акции `get_last_data` возвращает `Decimal`-цену и время
   котировки. `quotation_to_decimal` учитывает `units` и `nano`.
4. `calculate_trend` выставляет `is_trend_high`: `True`, если предыдущей цены
   нет или текущая цена не ниже предыдущей; `False`, если цена снизилась.
5. `share.save(update_fields=["last_price", "is_trend_high", "updated_at"])`
   обновляет текущее состояние, включая `auto_now`-поле.
6. `PriceHistory.objects.get_or_create(share=..., quoted_at=...)` сохраняет
   снимок; повторная котировка с тем же временем не создаёт дубль.
7. Ошибка по отдельной акции или сохранению снимка логируется и не прерывает
   обработку остальных акций.

### 6.9 Сценарий H — импорт справочника

`python manage.py add_shares` → `get_shares()` → Tinkoff
`client.instruments.shares()` → для каждого инструмента
`Share.objects.update_or_create(figi=...)` с обновлением `name`, `isin`,
`ticker`, `currency`, `uid`. Команда выводит количество созданных,
обновлённых и пропущенных записей; при отсутствии токена или SDK выбрасывает
`CommandError` без traceback.

## 7. Восстановленные функциональные требования

Требования восстановлены по исходному поведению приложения и приведены в
`REQUIREMENTS.md`. Ниже — полный перечень с отметкой о текущей реализации.
Если текущее поведение осознанно отличается от исходного, это указано в
столбце «Реализация» и дополнительно описано в разделе 7.9.

### 7.1 Просмотр акций

| ID | Требование | Реализация |
|---|---|---|
| FR-01 | Список всех акций по `GET /` без аутентификации | `ShareListView`, публичный |
| FR-02 | Колонки «Тикер», «Название», «ISIN», «Текущая цена»; цена с валютой | `list.html`; при отсутствии цены выводится «—» |
| FR-03 | Тикер — ссылка на детальную страницу | `{% url 'dashboard:detail' share.id %}` |
| FR-04 | При отсутствии акций — сообщение «Акций еще нет» | `list.html`, ветка `{% else %}` |
| FR-05 | Сортировка по наименованию компании | `ShareListView.ordering = ["name"]` |
| FR-06 | Пагинация по 100 записей с навигацией | `paginate_by = 100`, блок `page_obj` |
| FR-07 | Зелёная подсветка при росте, розовая иначе | `is_trend_high`; для акций без цены подсветка не применяется |
| FR-08 | «Добавить» и «Управление» только для аутентифицированных | `{% if user.is_authenticated %}` |
| FR-09 | Детальная страница `GET /<pk>` без аутентификации: название, цена с валютой, время обновления | `ShareDetailView`, `detail.html`; для отсутствующего `pk` — 404 |
| FR-10 | Детальная страница содержит график исторических цен | `plot_div` из `get_graph` |
| FR-11 | График по дневным свечам за 180 дней, HTML-фрагмент plotly без ссылки на plotly | `graph.py`: `CANDLE_INTERVAL_DAY`, `timedelta(days=180)`, `include_plotlyjs="cdn"`, `displayModeBar=False`; при ошибке — сообщение вместо 500 |

### 7.2 Пользователи

| ID | Требование | Реализация |
|---|---|---|
| FR-12 | Страница регистрации `GET /user/registration/` с `email`, `password1`, `password2` | `RegistrationView`, `RegistrationForm` |
| FR-13 | Создание пользователя, автоматический вход и редирект на список | `RegistrationView.form_valid` |
| FR-14 | Проверка совпадения паролей с сообщением «Введенные пароли не совпадают» | `RegistrationForm.clean` |
| FR-15 | Проверка, что e-mail ещё не зарегистрирован | `RegistrationForm.clean`, `iexact` |
| FR-16 | Страница входа `GET /user/login/` с полями e-mail и пароля | `LoginView`, `EmailAuthenticationForm` |
| FR-17 | Вход по e-mail в нижнем регистре и паролю; сессия и редирект на список | `EmailAuthenticationForm.clean_username`, `LoginView`; поддерживается `next` |
| FR-18 | При неверных данных — сообщение «Неверный логин или пароль! Повторите попытку.» | `EmailAuthenticationForm.error_messages` |
| FR-19 | Выход по `GET /user/logout/` с завершением сессии и редиректом на список | **Изменено:** выход только POST; GET возвращает 405 |
| FR-20 | В шапке e-mail и «Выход» для вошедшего, «Войти» для анонимного | `base.html` |
| FR-21 | CRUD акций только для аутентифицированных; иначе редирект на список | **Изменено:** редирект на `/user/login/?next=...` |

### 7.3 Управление акциями (HTML)

| ID | Требование | Реализация |
|---|---|---|
| FR-22 | Форма создания `GET /create` со всеми полями `Share` | `ShareCreateView`, `ShareModelForm.Meta.fields = "__all__"` |
| FR-23 | Сохранение корректной формы `POST /create` и редирект на список | `CreateView`, `success_url = dashboard:index` |
| FR-24 | Форма редактирования `GET/POST /update/<pk>` и редирект на список | `ShareUpdateView` |
| FR-25 | Подтверждение удаления `GET /delete/<pk>` с названием акции | `ShareDeleteView`, `delete.html` |
| FR-26 | Удаление только по `POST /delete/<pk>` и редирект на список | POST-форма с `csrf_token` |
| FR-27 | Проверка уникальности `figi`, `ticker`, `uid` и максимальных длин | `ShareModelForm` на базе модели |

### 7.4 REST API

| ID | Требование | Реализация |
|---|---|---|
| FR-28 | Список акций `GET /api/v1/shares/` | `ShareViewSet`, `DefaultRouter` |
| FR-29 | Одна акция `GET /api/v1/shares/<pk>/`, 404 для отсутствующей | `ModelViewSet`, тест |
| FR-30 | Создание `POST /api/v1/shares/`, 201 | `ModelViewSet.create`; `uid` генерируется, если не передан |
| FR-31 | Полное и частичное обновление `PUT/PATCH` | `ModelViewSet.update`, `partial_update` |
| FR-32 | Удаление `DELETE`, 204 | `ModelViewSet.destroy` |
| FR-33 | Ошибка 400 при некорректных данных | Валидация `ShareSerializer` |
| FR-34 | Пагинация по 100 с `limit` и `offset` | `LimitOffsetPagination`, `PAGE_SIZE = 100` |
| FR-35 | Фильтрация по точным `name` и `ticker` | `ShareFilter.Meta.fields` |
| FR-36 | Сортировка по `name` и `ticker` через `ordering` | `OrderingFilter` |
| FR-37 | Поиск по префиксу `name` через `search` | `SearchFilter`, `search_fields = ["$name"]` |
| FR-38 | Ответ содержит `id`, `figi`, `isin`, `name`, `ticker`, `currency`, `last_price`, `is_trend_high`, `updated_at` | **Дополнено:** также возвращается `uid` |
| FR-39 | Корневой маршрут `GET /api/v1/` | `DefaultRouter` |
| FR-40 | API не требует аутентификации для чтения и изменения | По умолчанию открыт; **изменяемо** настройкой `API_REQUIRE_AUTH` |

### 7.5 Фоновое обновление цен

| ID | Требование | Реализация |
|---|---|---|
| FR-41 | Периодический запуск `update_last_price` через Celery Beat | `config/celery.py`, интервал 5 минут |
| FR-42 | Перебор всех акций и запрос цены по `figi` | `Share.objects.all()`, `get_last_data` |
| FR-43 | Запись `last_price` и `is_trend_high` | `save(update_fields=...)`; дополнительно обновляется `updated_at` и создаётся `PriceHistory` |
| FR-44 | `is_trend_high=False`, если предыдущая цена строго больше новой; иначе `True` | `calculate_trend`; при отсутствии предыдущей цены — `True` |
| FR-45 | Ошибки по акции/API не прерывают остальные и логируются | `try/except` по каждой акции, `logger.warning/exception` |
| FR-46 | Лимит задачи 30 минут, часовой пояс `Europe/Moscow` | `CELERY_TASK_TIME_LIMIT`, `CELERY_TIMEZONE` |

### 7.6 Импорт справочника акций

| ID | Требование | Реализация |
|---|---|---|
| FR-47 | Management-команда `add_shares` для загрузки акций из Tinkoff | `Command.handle` |
| FR-48 | Сохранение `figi`, `name`, `isin`, `ticker`, `currency`, `uid` без дублей | `update_or_create(figi=...)`: существующие обновляются, новые создаются |

### 7.7 Администрирование и логирование

| ID | Требование | Реализация |
|---|---|---|
| FR-49 | Просмотр и редактирование акций в Django Admin | `ShareAdmin`; дополнительно `PriceHistoryAdmin` |
| FR-50 | Логгер `main` пишет в консоль и файл `app.logs` в формате `[module asctime levelname] message` | `config/settings.py:LOGGING` |

### 7.8 Новая функциональность: история рыночных цен

Требования к новой функциональности (вариант 3) полностью описаны в
`NEW_FEATURE.md`; ниже — сводка.

| ID | Требование | Реализация |
|---|---|---|
| FR-H01 | При каждом успешном получении цены сохранять снимок: акцию, цену и время котировки | `update_last_price`, `PriceHistory` |
| FR-H02 | Не создавать дубль для одной пары «акция + время котировки» | `UNIQUE(share, quoted_at)` и `get_or_create` |
| FR-H03 | Если API не вернул время котировки, использовать текущее время сервера | `normalize_quoted_at` |
| FR-H04 | Ошибка сохранения снимка не прерывает обновление остальных акций и самой цены | `try/except DatabaseError` |
| FR-H05 | Страница истории `GET /history/<id>`, 404 для отсутствующей акции | `ShareHistoryView` |
| FR-H06 | Периоды 7/30/90/180/365 дней; по умолчанию 30; недопустимое значение заменяется на 30 | `get_period_days` |
| FR-H07 | Показывать количество точек, первую, последнюю, минимальную и максимальную цену | `calculate_statistics` |
| FR-H08 | Считать абсолютное и процентное изменение; при первой цене 0 процент не считать | `calculate_statistics` |
| FR-H09 | Строить график по данным БД, а не по запросу в Tinkoff | `build_history_graph` |
| FR-H10 | Прореживать график до 500 точек с сохранением первой и последней | `downsample`, `MAX_GRAPH_POINTS=500`; первая и последняя точки сохраняются |
| FR-H11 | Показывать 20 последних снимков выбранного периода | `recent_records` |
| FR-H12 | При отсутствии данных показывать сообщение, а не ошибку | пустое состояние `history.html` |
| FR-H13 | Ссылка на историю со страницы акции | кнопка «История цен» в `detail.html` |
| FR-H14 | Снимки доступны в Django Admin с фильтрацией и поиском | `PriceHistoryAdmin` |

### 7.9 Отклонения от исходных требований и осознанные изменения

| Пункт | Исходное поведение | Текущее поведение | Причина |
|---|---|---|---|
| FR-19 | Выход по GET | Выход только POST, GET → 405 | Защита от CSRF; форма выхода обновлена |
| FR-21 | Редирект на главную при отсутствии входа | Редирект на `/user/login/?next=...` | Пользователь понимает, что нужно войти |
| FR-38 / BR-20 | В API не было `uid` | `uid` возвращается; необязателен при создании, генерируется UUID | Устранение D-01 и сохранение совместимости |
| FR-40 / D-03 | API полностью открыт | По умолчанию открыт; `API_REQUIRE_AUTH=true` требует вход для записи | Совместимость с исходными клиентами |
| FR-43 / BR-08 | `QuerySet.update()` не обновлял `updated_at` | `save(update_fields=...)`, включая `updated_at` | Корректное время последнего обновления |
| FR-44 | Сравнение с `None` и общий `except` искажали тренд | `calculate_trend`: `None` → `True`, иначе `current >= previous` | Предсказуемая семантика |
| FR-48 / BR-24 | `get_or_create` по всем полям мог падать на дубле `figi` | `update_or_create(figi=...)` | Идемпотентный импорт |
| FR-11 / D-16 | Ошибка Tinkoff API давала 500 | `get_graph` возвращает `None`, шаблон показывает сообщение | Страница остаётся доступной |
| FR-07 | Всегда зелёная/розовая подсветка | Для акций без цены — нейтральная ячейка | Нет данных для оценки тренда |
| BR-25 / D-13 | Пароли не проверялись валидаторами | Вызывается `validate_password` | Безопасность учётных записей |

Дополнительно:

- **D-03** закрыт настройкой, а не жёстким требованием входа: по умолчанию
  сохранена совместимость.
- **D-21** (нет пользовательской сортировки в HTML) и **D-22** (у акции нет
  владельца) задокументированы как ограничения, а не как дефекты
  работоспособности. Подробности — в `AUDIT.md`.
- Всего из 22 зафиксированных дефектов 19 исправлены, D-03 вынесен в настройку,
  D-21 и D-22 остаются осознанными ограничениями.

## 8. Проверка, тесты и ограничения

### 8.1 Автоматические проверки

```text
python manage.py check                    -> no issues
python manage.py makemigrations --check   -> No changes detected
python manage.py test                     -> Ran 62 tests ... OK
coverage report                           -> 95%
ruff check .                              -> All checks passed
```

Тестовое покрытие включает:

- модель `Share`, `__str__`, расчёт тренда, преобразование котировок;
- HTML-список, карточку акции, 404, график и его отсутствие;
- создание, редактирование и удаление через HTML с проверкой прав;
- REST API: список, фильтры, сортировка, поиск, пагинация, CRUD, валидация,
  генерацию `uid` и сохранение `uid` при обновлении;
- задачу обновления цен, тренд, `updated_at`, изоляцию ошибок;
- команду `add_shares` и её идемпотентность;
- регистрацию, вход, выход, ошибки форм и регистронезависимую уникальность;
- историю цен: периоды, статистику, график, прореживание, уникальность,
  страницу, пустое состояние, 404, запись снимков и дедупликацию.

### 8.2 Проверка на реальном сервере

```text
GET /                         -> 200
GET /1                        -> 200
GET /history/1                -> 200
GET /history/1?days=7         -> 200
GET /history/1?days=365       -> 200
GET /history/9999             -> 404
GET /user/login/              -> 200
GET /user/registration/       -> 200
GET /api/v1/shares/           -> 200
GET /create (аноним)          -> 302 -> /user/login/?next=/create
```

Сценарий с CSRF и cookie: вход → создание → редактирование → удаление →
выход. API проверен на `POST/PATCH/DELETE` с кодами 201/200/204.

Локальная демонстрационная база `db.sqlite3` содержит три акции (AAPL, AMZN,
SBER) и 1095 снимков истории (по 365 дней на акцию), а также пользователя
`demo@example.com` / `DemoPass123!`. База не входит в репозиторий и не
появится в свежем клоне.

### 8.3 Поведение без Tinkoff API

- `python manage.py add_shares` завершается `CommandError` с понятным
  сообщением, без traceback.
- `update_last_price()` логирует предупреждение по каждой акции, возвращает 0 и
  не изменяет данные.
- Страница акции открывается, вместо графика выводится сообщение
  «График недоступен».
- Страница истории открывается и показывает пустое состояние; снимки не
  создаются, пока нет реальных котировок.

### 8.4 Ограничения

1. **API открыт по умолчанию.** Это сохранённая совместимость; для защиты
   записи нужно `API_REQUIRE_AUTH=true`.
2. **У акции нет владельца.** Справочник общий для всех аутентифицированных
   пользователей.
3. **Нет пользовательской сортировки в HTML-списке.** Сортировка
   фиксирована по `name`; сортировка доступна только в API.
4. **История не загружается ретроспективно.** Снимки начинают накапливаться
   после запуска Celery с настроенным `TINKOFF_TOKEN`.
5. **Нет ограничения срока хранения истории.** Очистка может быть добавлена
   отдельной периодической задачей.
6. **Нет отдельного REST-эндпоинта истории.** История доступна через
   веб-интерфейс и Django Admin; это сознательное ограничение минимального
   варианта.
7. **Tinkoff SDK не входит в основной `requirements.txt`.** Он ставится
   отдельно по инструкции из `README.md`; без него приложение работает в
   ограниченном режиме.
8. **Локальные демонстрационные данные не коммитятся.** `db.sqlite3`,
   `app.logs`, `.coverage` и `.env` исключены через `.gitignore`.

## 9. Связанные документы

| Документ | Содержание |
|---|---|
| `README.md` | Быстрый запуск, PostgreSQL, Tinkoff SDK, Celery, тесты, API |
| `REQUIREMENTS.md` | Восстановленные требования FR-01…FR-50, бизнес-правила, исходные дефекты |
| `AUDIT.md` | Аудит зависимостей, решения по D-01…D-22, проверка работоспособности |
| `NEW_FEATURE.md` | Обоснование выбора, FR-H01…FR-H14, архитектура и проверка истории цен |
| `ANALYSIS.md` | Текущее состояние приложения, архитектура, модель данных и требования |
