# Анализ архитектуры приложения Investing Demo

## 1. Назначение приложения и технологический стек

**Назначение:** Веб-приложение для мониторинга рыночных цен акций через API Тинькофф Инвестиций. Приложение позволяет просматривать список акций, отслеживать текущие цены и направления трендов, а также визуализировать исторические данные цен в виде графиков.

**Технологический стек:**

- **Backend:** Python 3 + Django 4.1.7
- **Frontend:** HTML-шаблоны Django + Bootstrap 3 + Plotly (графики) + jQuery + Font Awesome
- **База данных:** PostgreSQL (настраивается через Docker)
- **Очередь задач:** Celery + Redis (брокер)
- **API:** Django REST Framework
- **Формы:** django-crispy-forms + crispy-bootstrap3
- **Фильтрация:** django-filter
- **Интеграция с биржей:** tinkoff-investments (API Тинькофф Инвестиций)

---

## 2. Структура проекта и основные компоненты

```
aidd-topic-03-homework/
├── config/                    # Конфигурация Django-проекта
│   ├── settings.py            # Основные настройки приложения
│   ├── urls.py                # Корневые URL-маршруты
│   ├── celery.py              # Конфигурация Celery + beat-расписание
│   ├── wsgi.py / asgi.py      # WSGI/ASGI приложения
│
├── dashboard/                 # Основной модуль (акции)
│   ├── models.py              # Модель Share (акция)
│   ├── views.py               # View-классы (ListView, DetailView, CRUD)
│   ├── forms.py               # Модели формы ShareModelForm
│   ├── urls.py                # URL-маршруты dashboard
│   ├── admin.py               # Админ-панель
│   ├── tasks.py               # Celery-задачи (обновление цен)
│   ├── services/              # Сервисный слой
│   │   ├── market_data.py     # Получение данных через Tinkoff API
│   │   └── graph.py           # Генерация графиков Plotly
│   ├── api/v1/                # REST API
│   │   ├── views.py           # ShareViewSet
│   │   ├── serializer.py      # ShareSerializer
│   │   └── router.py          # DRF роутер
│   ├── management/commands/   # Команды Django
│   │   └── add_shares.py      # Загрузка списка акций из Tinkoff API
│   └── templates/dashboard/   # Шаблоны (base, list, detail, create, delete)
│
├── user/                      # Модуль аутентификации
│   ├── models.py              # Импортирует User из get_user_model()
│   ├── views.py               # AuthView, RegistrationView, LogoutView
│   ├── forms.py               # RegistrationForm, AuthForm
│   └── templates/user/        # Шаблоны авторизации и регистрации
│
├── requirements.txt           # Зависимости
├── docker-compose.yml         # PostgreSQL + Redis
├── manage.py                  # Django CLI
└── db.sqlite3                 # SQLite-бэкап (не используется)
```

---

## 3. Архитектура приложения и взаимодействие компонентов

Архитектура следует классическому паттерну **MVT (Model-View-Template)** Django:

```
┌─────────────────────────────────────────────────────────────┐
│                       Пользователь (Browser)                 │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTP-запросы
┌────────────────────────▼────────────────────────────────────┐
│                    URL Router (config/urls.py)               │
│  ┌────────────────────┐  ┌──────────────────────────────┐  │
│  │  dashboard/        │  │  user/                       │  │
│  │  - index (ListView)│  │  - login                     │  │
│  │  - detail (View)   │  │  - register                  │  │
│  │  - CRUD (CBV)      │  │  - logout                    │  │
│  └─────────┬──────────┘  └──────────────────────────────┘  │
│            │                                                 │
│  ┌─────────▼──────────────────────────────────────────┐    │
│  │              Views (dashboard/views.py)             │    │
│  │  • ShareListView -> render(list.html)              │    │
│  │  • ShareDetailView -> render(detail.html, graph)   │    │
│  │  • ShareCreateView -> form processing              │    │
│  │  • ShareUpdateView -> form processing              │    │
│  │  • ShareDeleteView -> delete record                │    │
│  └─────────┬──────────────────────────────────────────┘    │
│            │          ┌──────────────────────────┐          │
│  ┌─────────▼──────┐   │  Services               │          │
│  │  Models        │   │  • market_data.py       │          │
│  │  (Share)       │   │  • graph.py             │          │
│  └─────────┬──────┘   │   -> Tinkoff Invest API │          │
│            │          └──────────────────────────┘          │
│  ┌─────────▼──────────────────────────────────────────┐    │
│  │         Database (PostgreSQL)                       │    │
│  │         Table: dashboard_share                      │    │
│  └────────────────────────────────────────────────────┘    │
│                                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │  Celery Worker + Beat (tasks.py)                   │   │
│  │  • update_last_price() -- каждые 10 сек             │   │
│  │    -> market_data.get_last_data() -> обновляет       │   │
│  │       Share.last_price и Share.is_trend_high        │   │
│  └────────────────────────────────────────────────────┘   │
│                                                            │
│  ┌────────────────────────────────────────────────────┐   │
│  │  REST API (dashboard/api/v1/)                      │   │
│  │  GET/POST/PUT/DELETE /api/v1/shares/               │   │
│  │  ShareViewSet + ShareSerializer                    │   │
│  └────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

**Поток данных:**

1. Пользователь открывает список акций -> `ShareListView` -> `Share.objects.all()` -> `list.html`
2. Пользователь открывает детальную страницу -> `ShareDetailView` -> `get_graph(share)` (Tinkoff API -> Plotly) -> `detail.html`
3. Celery Beat запускает `update_last_price()` каждые 10 секунд -> `market_data.get_last_data()` (Tinkoff API) -> обновляет `Share` в БД
4. Команда `add_shares` загружает все доступные акции из Tinkoff API при старте

---

## 4. Используемые библиотеки и внешние зависимости

| Библиотека | Версия | Назначение |
|---|---|---|
| **Django** | 4.1.7 | Основной фреймворк |
| **djangorestframework** | 3.14.0 | REST API |
| **django-filter** | 22.1 | Фильтрация API |
| **django-crispy-forms** | 2.0 | Рендеринг форм |
| **crispy-bootstrap3** | 2022.1 | Стили Bootstrap 3 |
| **tinkoff-investments** | 0.2.0b50 | API Тинькофф Инвестиций |
| **plotly** | 5.13.1 | Графики |
| **celery** | 5.2.7 | Асинхронные задачи |
| **redis** | 4.5.1 | Брокер для Celery |
| **psycopg2-binary** | 2.9.5 | PostgreSQL драйвер |
| **pydantic** | 1.10.6 | Валидация данных |

---

## 5. Модель данных

### Сущность: Share (Акция)

| Поле | Тип | Описание |
|---|---|---|
| `id` | BigAutoField | Первичный ключ |
| `figi` | CharField (unique) | FIGI-идентификатор акции |
| `isin` | CharField | ISIN-идентификатор |
| `name` | CharField | Наименование компании |
| `ticker` | CharField (unique, max=10) | Тикер акции |
| `currency` | CharField | Валюта цены |
| `uid` | CharField (unique) | Уникальный UID из Tinkoff API |
| `last_price` | FloatField (null) | Текущая цена |
| `is_trend_high` | BooleanField (null) | Флаг роста цены |
| `updated_at` | DateTimeField (auto_now) | Время последнего обновления |

**Связи:**

- `User` (Django auth) -> `Share`: нет прямых связей (акции общие для всех пользователей)
- `Share` <-> `Tinkoff Invest API`: внешняя зависимость через `figi`

---

## 6. Механизмы обработки пользовательских запросов и взаимодействия с БД

### HTTP-маршруты

| URL | View | Метод | Описание |
|---|---|---|---|
| `/` | `ShareListView` | GET | Список акций с пагинацией |
| `/<int:pk>` | `ShareDetailView` | GET | Детали акции + график |
| `create` | `ShareCreateView` | GET/POST | Добавление акции (только авторизованным) |
| `update/<int:pk>` | `ShareUpdateView` | GET/POST | Редактирование (только авторизованным) |
| `delete/<int:pk>` | `ShareDeleteView` | GET/POST | Удаление (только авторизованным) |
| `/user/login/` | `AuthView` | GET/POST | Авторизация |
| `/user/registration/` | `RegistrationView` | GET/POST | Регистрация |
| `/user/logout/` | `LogoutView` | GET | Выход |
| `/api/v1/shares/` | `ShareViewSet` | GET/POST/PUT/DELETE | REST API |

### Механизмы взаимодействия с БД

1. **ORM Django:** Все операции с `Share` выполняются через Django ORM (`Share.objects.all()`, `Share.objects.get()`, `Share.objects.filter().update()`, `Share.objects.get_or_create()`)
2. **Автоматическое обновление цен:** Celery Beat запускает задачу `update_last_price()` каждые 10 секунд, которая обращается к Tinkoff API и обновляет `last_price` и `is_trend_high` для всех акций
3. **Загрузка акций:** Команда `python manage.py add_shares` загружает полный список акций из Tinkoff API через `client.instruments.shares()`
4. **Графики:** При открытии детальной страницы акции вызывается `get_graph(share)`, который получает 180 дней дневных свечей через `client.get_all_candles()` и рендерит Plotly-график

---

## Ключевые архитектурные особенности

1. **Двухуровневый доступ:** CRUD-операции через HTML-интерфейс (требует авторизации) + REST API (без авторизации)
2. **Асинхронное обновление:** Celery + Redis обеспечивают автоматическое обновление цен без блокировки веб-запросов
3. **Внешняя интеграция:** Всё взаимодействие с биржевыми данными происходит через Tinkoff Invest API (токен хранится в `TINKOFF_TOKEN`)
4. **Аутентификация:** Пользователи регистрируются по email (без стандартного Django username), авторизация через `django.contrib.auth`
5. **Миксин авторизации:** `IsUserAuthenticatedMixin` перенаправляет неавторизованных пользователей на главную страницу вместо стандартной страницы входа
