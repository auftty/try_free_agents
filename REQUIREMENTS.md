# REQUIREMENTS.md

Восстановленные функциональные требования к приложению «Investing Demo» (Django‑проект `config`, приложения `dashboard` и `user`).

Документ описывает **фактически реализованное** поведение. Дефекты, противоречия и неоднозначности вынесены в раздел 5 и не рассматриваются как требования.

Обозначения: `FR` — функциональное требование, `UC` — сценарий, `BR` — бизнес‑правило/ограничение, `D` — дефект/неоднозначность.

---

## 1. Основные функциональные возможности

| № | Возможность | Подтверждение |
|---|---|---|
| F-01 | Просмотр списка акций с ценой и индикацией динамики | `dashboard/views.py:ShareListView`, `dashboard/templates/dashboard/list.html` |
| F-02 | Просмотр карточки акции с графиком за 180 дней | `dashboard/views.py:ShareDetailView.get`, `dashboard/services/graph.py:get_graph` |
| F-03 | Регистрация пользователя по e‑mail и паролю с автоматическим входом | `user/views.py:RegistrationView.post`, `user/forms.py:RegistrationForm` |
| F-04 | Вход и выход пользователя | `user/views.py:AuthView.post`, `user/views.py:LogoutView.get` |
| F-05 | Создание, редактирование и удаление акций через HTML‑формы (только для аутентифицированных) | `dashboard/views.py:ShareCreateView`, `ShareUpdateView`, `ShareDeleteView` |
| F-06 | CRUD‑API по акциям с пагинацией, фильтрацией, сортировкой и поиском | `dashboard/api/v1/views.py:ShareViewSet`, `ShareFilter` |
| F-07 | Периодическое обновление последней цены и признака роста/падения | `dashboard/tasks.py:update_last_price`, `config/celery.py:13-18` |
| F-08 | Первичная загрузка справочника акций из Tinkoff Invest API | `dashboard/management/commands/add_shares.py:Command.handle` |
| F-09 | Администрирование акций через Django Admin | `dashboard/admin.py:ShareAdmin` |
| F-10 | Логирование работы внешних интеграций и фоновой задачи | `config/settings.py:LOGGING`, `dashboard/tasks.py`, `dashboard/services/market_data.py` |

---

## 2. Основные сценарии взаимодействия пользователя

### UC-01. Просмотр списка акций (анонимный пользователь)

1. Пользователь открывает `GET /`.
2. `config/urls.py` → `dashboard/urls.py` (`path("", ShareListView.as_view(), name="index")`).
3. `ShareListView` выбирает все `Share`, сортирует по `name`, разбивает по 100 (`dashboard/views.py:ShareListView`).
4. Рендерится `dashboard/templates/dashboard/list.html`: колонки «Тикер», «Название», «ISIN», «Текущая цена»; тикер — ссылка на детальную страницу.
5. Признак `is_trend_high` определяет цвет ячейки цены; кнопка «Добавить» и колонка «Управление» не отображаются (`{% if user.is_authenticated %}`).

### UC-02. Просмотр карточки акции

1. Пользователь нажимает на тикер → `GET /<pk>`.
2. `dashboard/views.py:ShareDetailView.get` загружает акцию по `id`.
3. `dashboard/services/graph.py:get_graph` запрашивает дневные свечи за 180 дней по `figi` и строит график через plotly.
4. Шаблон `dashboard/templates/dashboard/detail.html` показывает название, текущую цену с валютой, время обновления и график.

### UC-03. Регистрация

1. `GET /user/registration/` — форма с полями `email`, `password1`, `password2` (`user/forms.py:RegistrationForm`).
2. `POST /user/registration/` → `RegistrationView.post` → `form.is_valid()`.
3. `RegistrationForm.clean` проверяет совпадение паролей и отсутствие e‑mail в базе.
4. `RegistrationForm.save` создаёт пользователя (`User.objects.create_user(email, email, password)`), выполняется `authenticate` и `login`.
5. Редирект на `dashboard:index`.

### UC-04. Вход

1. `GET /user/login/` — форма `email` + `password`.
2. `POST /user/login/` → `user/views.py:AuthView.post` → `authenticate(username=email.lower(), password=...)`.
3. При успехе — `login(request, user)` и редирект на `dashboard:index`.
4. При ошибке — повторный рендер `user/auth.html` с сообщением «Неверный логин или пароль! Повторите попытку.»

### UC-05. Выход

`GET /user/logout/` → `user/views.py:LogoutView.get` → `logout(request)` → редирект на `dashboard:index`.

### UC-06. Создание акции

1. Аутентифицированный пользователь нажимает «Добавить» → `GET /create`.
2. `IsUserAuthenticatedMixin.test_func` пропускает пользователя; `CreateView` рендерит `dashboard/create.html` с `ShareModelForm` (все поля модели).
3. `POST /create` → валидация формы → `form.save()` (INSERT) → редирект на `dashboard:index`.

### UC-07. Редактирование акции

`GET /update/<pk>` — форма с текущими значениями; `POST /update/<pk>` → `ShareUpdateView` → `form.save()` (UPDATE) → редирект на `dashboard:index`.

### UC-08. Удаление акции

`GET /delete/<pk>` — страница подтверждения с названием акции; `POST /delete/<pk>` → `ShareDeleteView` → `object.delete()` (DELETE) → редирект на `dashboard:index`.

### UC-09. Работа через REST API

1. `GET /api/v1/shares/` — список с пагинацией (`limit`/`offset`), фильтрами `name`/`ticker`, сортировкой `ordering`, поиском `search`.
2. `GET /api/v1/shares/<pk>/` — одна акция.
3. `POST /api/v1/shares/` — создание; `PUT/PATCH /api/v1/shares/<pk>/` — изменение; `DELETE /api/v1/shares/<pk>/` — удаление (`dashboard/api/v1/router.py:router`, `dashboard/api/v1/views.py:ShareViewSet`).
4. `GET /api/v1/` — корневой список API, формируемый `DefaultRouter`.

### UC-10. Фоновое обновление цен

1. Celery Beat по расписанию публикует задачу `dashboard.tasks.update_last_price` (интервал 10 с, `config/celery.py:13-18`).
2. Worker перебирает все `Share`, для каждой вызывает `dashboard/services/market_data.py:get_last_data`.
3. Значения `last_price` и `is_trend_high` записываются через `QuerySet.update()` (`dashboard/tasks.py:24-26`).

### UC-11. Первичное наполнение базы

`python manage.py add_shares` → `dashboard/management/commands/add_shares.py:Command.handle` → `client.instruments.shares()` → `Share.objects.get_or_create(...)` для каждого инструмента.

---

## 3. Бизнес‑правила, проверки и ограничения

| № | Правило | Подтверждение |
|---|---|---|
| BR-01 | `figi` обязательно и уникально; максимум 255 символов | `dashboard/models.py:Share.figi` |
| BR-02 | `isin` обязательно; максимум 255 символов; уникальность не требуется | `dashboard/models.py:Share.isin` |
| BR-03 | `name` обязательно; максимум 255 символов; отображается как «Наименование компании» | `dashboard/models.py:Share.name` |
| BR-04 | `ticker` обязателен, уникален; максимум 10 символов | `dashboard/models.py:Share.ticker` |
| BR-05 | `currency` обязательна; максимум 20 символов | `dashboard/models.py:Share.currency` |
| BR-06 | `uid` обязателен и уникален; максимум 255 символов | `dashboard/models.py:Share.uid` |
| BR-07 | `last_price` и `is_trend_high` могут быть пустыми (`null`/`blank`) | `dashboard/models.py:Share.last_price`, `is_trend_high` |
| BR-08 | `updated_at` заполняется автоматически при сохранении модели (`auto_now`) | `dashboard/models.py:Share.updated_at` |
| BR-09 | Список акций сортируется по `name`; размер страницы — 100 | `dashboard/views.py:ShareListView.ordering`, `paginate_by` |
| BR-10 | График строится по дневным свечам (`CANDLE_INTERVAL_DAY`) за последние 180 дней | `dashboard/services/graph.py:get_graph` |
| BR-11 | Пароли при регистрации должны совпадать | `user/forms.py:RegistrationForm.clean` |
| BR-12 | E‑mail при регистрации должен быть уникальным (проверка `User.objects.filter(email=email)`) | `user/forms.py:RegistrationForm.clean` |
| BR-13 | E‑mail обязателен и должен быть валидным; пароли обязательны | `user/forms.py:RegistrationForm`, `AuthForm` |
| BR-14 | При входе e‑mail приводится к нижнему регистру и используется как `username` | `user/views.py:AuthView.post`; `user/forms.py:RegistrationForm.save` |
| BR-15 | Создание, изменение и удаление акций доступны только аутентифицированным пользователям; иначе редирект на главную | `dashboard/views.py:IsUserAuthenticatedMixin` |
| BR-16 | Удаление выполняется только после подтверждения через POST‑форму | `dashboard/templates/dashboard/delete.html`, `dashboard/views.py:ShareDeleteView` |
| BR-17 | API отдаёт по 100 записей на страницу (`LimitOffsetPagination`) | `config/settings.py:REST_FRAMEWORK` |
| BR-18 | API фильтрует по точному значению `name` и `ticker` | `dashboard/api/v1/views.py:ShareFilter.Meta.fields` |
| BR-19 | API сортирует по `name` и `ticker`; поиск — по префиксу `name` (`$name`) | `dashboard/api/v1/views.py:ShareViewSet` |
| BR-20 | API сериализует поля `id, figi, isin, name, ticker, currency, last_price, is_trend_high, updated_at` (без `uid`) | `dashboard/api/v1/serializer.py:ShareSerializer.Meta.fields` |
| BR-21 | Celery: часовой пояс `Europe/Moscow`, лимит задачи 30 минут, отслеживание запуска включено, eager‑режим выключен | `config/settings.py:136-144` |
| BR-22 | Брокер Celery — Redis `redis://127.0.0.1:6379/0` | `config/settings.py:141` |
| BR-23 | Цена из Tinkoff берётся как целая часть (`price.units`), без `nano` | `dashboard/services/market_data.py:get_last_data` |
| BR-24 | Импорт акций не обновляет существующие записи, а только создаёт отсутствующие по полному набору атрибутов | `dashboard/management/commands/add_shares.py:Command.handle` |
| BR-25 | Пароль пользователя не проверяется настроенными `AUTH_PASSWORD_VALIDATORS` | `config/settings.py:106-119`; `user/forms.py:RegistrationForm.save` (используется `create_user`, валидаторы не вызываются) |

---

## 4. Функциональные требования

### 4.1. Просмотр акций

**FR-01.** Система должна отображать список всех акций по адресу `GET /` без требования аутентификации.
*Подтверждение:* `config/urls.py:urlpatterns`, `dashboard/urls.py` (`path("", ShareListView.as_view(), name="index")`), `dashboard/views.py:ShareListView` (наследует `ListView`, без миксина доступа).

**FR-02.** Список должен содержать колонки «Тикер», «Название», «ISIN», «Текущая цена»; значение цены выводится вместе с валютой.
*Подтверждение:* `dashboard/templates/dashboard/list.html` (`<th>`‑заголовки и `{{share.last_price}} {{ share.currency }}`).

**FR-03.** Тикер в списке должен быть ссылкой на детальную страницу акции.
*Подтверждение:* `dashboard/templates/dashboard/list.html` (`{% url 'dashboard:detail' share.id %}`), `dashboard/urls.py` (`path("<int:pk>", ...)`).

**FR-04.** Если акций нет, система должна выводить сообщение «Акций еще нет».
*Подтверждение:* `dashboard/templates/dashboard/list.html` (`{% else %}<p>Акций еще нет</p>` для пустого `share_list`).

**FR-05.** Список должен сортироваться по наименованию компании.
*Подтверждение:* `dashboard/views.py:ShareListView.ordering = ["name"]`.

**FR-06.** Список должен быть постраничным с размером страницы 100 записей и элементами навигации «предыдущая/следующая/номера страниц».
*Подтверждение:* `dashboard/views.py:ShareListView.paginate_by = 100`, `dashboard/templates/dashboard/list.html` (блок `page_obj`).

**FR-07.** Цена в списке должна подсвечиваться зелёным (`mediumseagreen`), если `is_trend_high` истинно, и розовым (`palevioletred`) в остальных случаях.
*Подтверждение:* `dashboard/templates/dashboard/list.html` (`{% if share.is_trend_high %}<td style="background-color: mediumseagreen">{% else %}<td style="background-color: palevioletred">`).

**FR-08.** Кнопка «Добавить» и колонка «Управление» должны отображаться только аутентифицированным пользователям.
*Подтверждение:* `dashboard/templates/dashboard/list.html` (`{% if user.is_authenticated %}` вокруг кнопки и колонки).

**FR-09.** Система должна отображать детальную страницу акции по `GET /<pk>` без требования аутентификации: наименование, текущую цену с валютой, время последнего обновления.
*Подтверждение:* `dashboard/urls.py` (`name="detail"`), `dashboard/views.py:ShareDetailView.get`, `dashboard/templates/dashboard/detail.html`.

**FR-10.** Детальная страница должна содержать график исторических цен акции.
*Подтверждение:* `dashboard/views.py:ShareDetailView.get` (`{"plot_div": get_graph(share), ...}`), `dashboard/templates/dashboard/detail.html` (`{{ plot_div }}` внутри `{% autoescape off %}`).

**FR-11.** График должен строиться по дневным свечам за 180 дней до текущего момента и выводиться как HTML‑фрагмент plotly без ссылки на сайт plotly.
*Подтверждение:* `dashboard/services/graph.py:get_graph` (`CandleInterval.CANDLE_INTERVAL_DAY`, `now() - timedelta(days=180)`, `output_type="div"`, `show_link=False`).

### 4.2. Пользователи

**FR-12.** Система должна предоставлять страницу регистрации `GET /user/registration/` с полями `email`, `password1`, `password2`.
*Подтверждение:* `user/urls.py` (`name="registration"`), `user/views.py:RegistrationView.get`, `user/forms.py:RegistrationForm`.

**FR-13.** При корректном заполнении формы регистрации система должна создать пользователя, аутентифицировать его и перенаправить на список акций.
*Подтверждение:* `user/views.py:RegistrationView.post` (`form.save()`, `login(request, user)`, `redirect("dashboard:index")`), `user/forms.py:RegistrationForm.save` (`User.objects.create_user(email, email, password)`).

**FR-14.** При регистрации система должна проверять совпадение `password1` и `password2` и выводить ошибку «Введенные пароли не совпадают».
*Подтверждение:* `user/forms.py:RegistrationForm.clean` (`ValidationError(["Введенные пароли не совпадают"])`).

**FR-15.** При регистрации система должна проверять, что e‑mail ещё не зарегистрирован, и выводить соответствующее сообщение об ошибке.
*Подтверждение:* `user/forms.py:RegistrationForm.clean` (`User.objects.filter(email=email)`, `ValidationError([... "Данный e-mail уже зарегистрирован! ..."])`).

**FR-16.** Система должна предоставлять страницу входа `GET /user/login/` с полями `email` и `password`.
*Подтверждение:* `user/urls.py` (`name="auth"`), `user/views.py:AuthView.get`, `user/forms.py:AuthForm`.

**FR-17.** При входе система должна аутентифицировать пользователя по e‑mail (в нижнем регистре) и паролю; при успехе — создавать сессию и перенаправлять на список акций.
*Подтверждение:* `user/views.py:AuthView.post` (`authenticate(request, username=form.data["email"].lower(), password=form.data["password"])`, `login`, `redirect`).

**FR-18.** При неверных учётных данных система должна повторно показать форму входа с сообщением «Неверный логин или пароль! Повторите попытку.».
*Подтверждение:* `user/views.py:AuthView.post` (`else: render(..., {"error": "Неверный логин или пароль! Повторите попытку."})`), `user/templates/user/auth.html` (`{{ error }}`).

**FR-19.** Система должна предоставлять выход из учётной записи по `GET /user/logout/` с завершением сессии и перенаправлением на список акций.
*Подтверждение:* `user/urls.py` (`name="logout"`), `user/views.py:LogoutView.get` (`logout(request)`, `redirect("dashboard:index")`).

**FR-20.** В шапке сайта для аутентифицированного пользователя должны отображаться его e‑mail и кнопка «Выход», для анонимного — кнопка «Войти».
*Подтверждение:* `dashboard/templates/dashboard/base.html` (`{% if user.is_authenticated %}` … `{{ user.email }}` … `{% url 'user:logout' %}` / `{% url 'user:auth' %}`).

**FR-21.** Создание, редактирование и удаление акций должны быть доступны только аутентифицированным пользователям; при отсутствии аутентификации система должна перенаправлять на список акций.
*Подтверждение:* `dashboard/views.py:IsUserAuthenticatedMixin.test_func`, `IsUserAuthenticatedMixin.handle_no_permission` (`redirect("dashboard:index")`), использование миксина в `ShareCreateView`, `ShareUpdateView`, `ShareDeleteView`.

### 4.3. Управление акциями (HTML)

**FR-22.** Аутентифицированный пользователь должен иметь возможность открыть форму создания акции `GET /create`; форма должна содержать все поля модели `Share`.
*Подтверждение:* `dashboard/urls.py` (`path("create", ...)`), `dashboard/views.py:ShareCreateView`, `dashboard/forms.py:ShareModelForm.Meta.fields = "__all__"`, `dashboard/templates/dashboard/create.html`.

**FR-23.** При отправке корректной формы создания `POST /create` система должна сохранить акцию и перенаправить на список акций.
*Подтверждение:* `dashboard/views.py:ShareCreateView` (`form_class`, `success_url = reverse_lazy("dashboard:index")`), `dashboard/templates/dashboard/create.html` (`method="post"`, `{% csrf_token %}`).

**FR-24.** Аутентифицированный пользователь должен иметь возможность открыть форму редактирования `GET /update/<pk>` с заполненными текущими значениями и сохранить изменения `POST /update/<pk>` с перенаправлением на список.
*Подтверждение:* `dashboard/urls.py` (`path("update/<int:pk>", ...)`), `dashboard/views.py:ShareUpdateView` (`model = Share`, `form_class = ShareModelForm`, `success_url`).

**FR-25.** Аутентифицированный пользователь должен иметь возможность инициировать удаление `GET /delete/<pk>`; перед удалением выводится подтверждение с названием акции.
*Подтверждение:* `dashboard/urls.py` (`path("delete/<int:pk>", ...)`), `dashboard/views.py:ShareDeleteView`, `dashboard/templates/dashboard/delete.html` (`{{ share.name }}`).

**FR-26.** Удаление должно выполняться только при отправке POST‑формы `POST /delete/<pk>` с последующим перенаправлением на список.
*Подтверждение:* `dashboard/templates/dashboard/delete.html` (`method="post"`, `{% csrf_token %}`), `dashboard/views.py:ShareDeleteView` (`success_url`).

**FR-27.** При создании и редактировании через HTML‑формы система должна проверять уникальность `figi`, `ticker`, `uid` и максимальные длины полей на уровне модели.
*Подтверждение:* `dashboard/forms.py:ShareModelForm` (ModelForm на базе `Share`), `dashboard/models.py:Share` (`unique=True`, `max_length`).

### 4.4. REST API

**FR-28.** API должно предоставлять список акций `GET /api/v1/shares/`.
*Подтверждение:* `config/urls.py` → `dashboard/urls.py` (`path("api/", ...)`) → `dashboard/api/urls.py` → `dashboard/api/v1/urls.py`, `dashboard/api/v1/router.py:router` (`router.register(r"shares", ShareViewSet)`), `dashboard/api/v1/views.py:ShareViewSet`.

**FR-29.** API должно предоставлять получение одной акции `GET /api/v1/shares/<pk>/` с кодом 404 для несуществующего `pk`.
*Подтверждение:* `dashboard/api/v1/router.py:router` (маршрут detail от `DefaultRouter`), `dashboard/api/v1/views.py:ShareViewSet` (`ModelViewSet`); проверка — `dashboard/tests.py:DashboardTests.test_share_detail_invalid`.

**FR-30.** API должно поддерживать создание акции `POST /api/v1/shares/` с кодом 201 и ответом, содержащим сохранённые поля.
*Подтверждение:* `dashboard/api/v1/views.py:ShareViewSet` (`ModelViewSet.create`), `dashboard/tests.py:DashboardTests.test_share_create`. Ограничение фактической работы — см. D-01.

**FR-31.** API должно поддерживать полное (`PUT`) и частичное (`PATCH`) обновление акции `PUT/PATCH /api/v1/shares/<pk>/`.
*Подтверждение:* `dashboard/api/v1/views.py:ShareViewSet` (`ModelViewSet.update`, `partial_update`), `dashboard/tests.py:DashboardTests.test_share_update`.

**FR-32.** API должно поддерживать удаление акции `DELETE /api/v1/shares/<pk>/` с кодом 204.
*Подтверждение:* `dashboard/api/v1/views.py:ShareViewSet` (`ModelViewSet.destroy`), `dashboard/tests.py:DashboardTests.test_share_delete`.

**FR-33.** API должно возвращать ошибку 400 при некорректных или неполных данных создания/обновления.
*Подтверждение:* `dashboard/api/v1/serializer.py:ShareSerializer` (обязательные поля модели), `dashboard/tests.py:DashboardTests.test_share_create_invalid`, `test_share_update_invalid`.

**FR-34.** API должно пагинировать выдачу по 100 записей с параметрами `limit` и `offset`.
*Подтверждение:* `config/settings.py:REST_FRAMEWORK` (`LimitOffsetPagination`, `PAGE_SIZE = 100`).

**FR-35.** API должно фильтровать список по точным значениям `name` и `ticker`.
*Подтверждение:* `dashboard/api/v1/views.py:ShareFilter` (`fields = ("name", "ticker")`), `ShareViewSet.filterset_class`.

**FR-36.** API должно поддерживать сортировку по `name` и `ticker` через параметр `ordering`.
*Подтверждение:* `dashboard/api/v1/views.py:ShareViewSet` (`OrderingFilter`, `ordering_fields = ["name", "ticker"]`).

**FR-37.** API должно поддерживать поиск по префиксу наименования через параметр `search`.
*Подтверждение:* `dashboard/api/v1/views.py:ShareViewSet` (`SearchFilter`, `search_fields = ["$name"]`).

**FR-38.** API должно возвращать в ответах поля `id`, `figi`, `isin`, `name`, `ticker`, `currency`, `last_price`, `is_trend_high`, `updated_at`.
*Подтверждение:* `dashboard/api/v1/serializer.py:ShareSerializer.Meta.fields`.

**FR-39.** API должно предоставлять корневой маршрут `GET /api/v1/` со списком доступных ресурсов.
*Подтверждение:* `dashboard/api/v1/router.py:router` (`DefaultRouter`), `dashboard/api/v1/urls.py` (`include(router.urls)`).

**FR-40.** API не должно требовать аутентификации для чтения и изменения данных (фактическое поведение: явные `permission_classes`/`authentication_classes` не заданы, действуют дефолты DRF).
*Подтверждение:* `dashboard/api/v1/views.py:ShareViewSet` (отсутствуют `permission_classes`), `config/settings.py:REST_FRAMEWORK` (не задан `DEFAULT_PERMISSION_CLASSES`).

### 4.5. Фоновое обновление цен

**FR-41.** Система должна периодически запускать задачу обновления цен `dashboard.tasks.update_last_price` через Celery Beat.
*Подтверждение:* `config/celery.py:app.conf.beat_schedule` (`"task": "dashboard.tasks.update_last_price"`, `"schedule": 10.0`).

**FR-42.** Задача должна перебирать все акции и для каждой запрашивать последнюю цену через Tinkoff Invest API по `figi`.
*Подтверждение:* `dashboard/tasks.py:update_last_price` (`Share.objects.all()`, `get_last_data(share)`), `dashboard/services/market_data.py:get_last_data` (`client.market_data.get_last_prices(figi=[share.figi])`).

**FR-43.** Задача должна записывать в акцию полученную цену `last_price` и признак `is_trend_high`.
*Подтверждение:* `dashboard/tasks.py:update_last_price` (`Share.objects.filter(id=share.id).update(last_price=last_price, is_trend_high=is_trend_high)`).

**FR-44.** Признак `is_trend_high` должен быть `False`, если предыдущая цена строго больше новой, и `True` в остальных случаях (включая равенство цен).
*Подтверждение:* `dashboard/tasks.py:update_last_price` (`if share.last_price > last_price: is_trend_high = False else: is_trend_high = True`).

**FR-45.** Ошибки по отдельной акции или по внешнему API не должны прерывать обработку остальных акций; они должны логироваться.
*Подтверждение:* `dashboard/tasks.py:update_last_price` (`try/except` вокруг каждой акции и вокруг сравнения, `logger.error(e)`), `config/settings.py:LOGGING` (logger `main`).

**FR-46.** Задача должна выполняться с ограничением времени 30 минут и в часовом поясе `Europe/Moscow`.
*Подтверждение:* `config/settings.py:CELERY_TASK_TIME_LIMIT`, `CELERY_TIMEZONE`.

### 4.6. Импорт справочника акций

**FR-47.** Система должна предоставлять management‑команду `add_shares` для загрузки списка акций из Tinkoff Invest API.
*Подтверждение:* `dashboard/management/commands/add_shares.py:Command.handle`.

**FR-48.** Команда должна сохранять для каждой акции `figi`, `name`, `isin`, `ticker`, `currency`, `uid`, не создавая дубликаты при полном совпадении этих атрибутов.
*Подтверждение:* `dashboard/management/commands/add_shares.py:Command.handle` (`Share.objects.get_or_create(figi=..., name=..., isin=..., ticker=..., currency=..., uid=...)`).

### 4.7. Администрирование и логирование

**FR-49.** Администратор должен иметь возможность просматривать и редактировать акции в Django Admin.
*Подтверждение:* `dashboard/admin.py:ShareAdmin` (`@admin.register(Share)`, `list_display`, `search_fields`, `fields`), `config/urls.py` (`path("admin/", admin.site.urls)`).

**FR-50.** Сообщения логгера `main` должны выводиться в консоль и в файл `app.logs` в формате `[module asctime levelname] message`.
*Подтверждение:* `config/settings.py:LOGGING` (`handlers.console`, `handlers.file`, `formatters.main_format`), использование `logger` в `dashboard/tasks.py` и `dashboard/services/market_data.py`.

---

## 5. Неоднозначности, противоречия и дефекты реализации

> Перечисленное ниже — **не требования**, а зафиксированные расхождения между заявленной/ожидаемой и фактической работой кода.

| № | Проблема | Подтверждение | Последствие |
|---|---|---|---|
| D-01 | `ShareSerializer` не содержит обязательное уникальное `uid`. Django подставляет пустую строку, поэтому создание через API работает только для первой записи; повторное создание нарушает `unique` | `dashboard/api/v1/serializer.py:ShareSerializer.Meta.fields`, `dashboard/models.py:Share.uid`; `dashboard/tests.py:test_share_create` создаёт запись один раз | Второй `POST /api/v1/shares/` → IntegrityError/500; тест этого не выявляет |
| D-02 | `ShareDetailView.get` не обрабатывает отсутствие акции | `dashboard/views.py:ShareDetailView.get` (`Share.objects.get(id=pk)`) | `GET /<несуществующий pk>` → 500 вместо 404 |
| D-03 | API не ограничивает доступ: `permission_classes` не заданы, дефолт DRF — `AllowAny` | `dashboard/api/v1/views.py:ShareViewSet`, `config/settings.py:REST_FRAMEWORK` | Любой клиент может создавать/изменять/удалять акции |
| D-04 | `ShareCreateView` не задаёт `model`, в отличие от `UpdateView`/`DeleteView` | `dashboard/views.py:ShareCreateView` | Работает только за счёт явного `form_class`; при его изменении форма сломается |
| D-05 | Имя задачи Beat `add-every-5-min` не соответствует интервалу 10 секунд | `config/celery.py:13-18` | Вводит в заблуждение при эксплуатации; цена обновляется каждые 10 с, а не 5 мин |
| D-06 | `QuerySet.update()` обходит `auto_now`, поэтому `updated_at` не меняется при фоновом обновлении | `dashboard/tasks.py:24-26`, `dashboard/models.py:Share.updated_at` | Детальная страница показывает устаревшее «время последнего обновления» |
| D-07 | Из Tinkoff берётся только `price.units`, дробная часть (`nano`) игнорируется; второй элемент ответа (`time`) не используется | `dashboard/services/market_data.py:get_last_data`; `dashboard/tasks.py:update_last_price` | Цена округляется до целого; фактическое время котировки теряется |
| D-08 | Сравнение `share.last_price > last_price` некорректно при `last_price is None` (перехватывается общим `except`, выставляется `True`) | `dashboard/tasks.py:update_last_price` | Первое обновление всегда даёт `is_trend_high = True`; семантика признака размыта |
| D-09 | `AuthView.post` не вызывает `form.is_valid()` и обращается к `form.data["email"]` напрямую | `user/views.py:AuthView.post` | Отсутствие поля в POST → `KeyError`/500; валидация e‑mail не выполняется |
| D-10 | `RegistrationView.post` в ветке ошибки обращается к `form.errors["__all__"]` | `user/views.py:RegistrationView.post` | Ошибка валидации отдельного поля (например, неверный e‑mail) → `KeyError`/500 |
| D-11 | `RegistrationForm.clean` обращается к `self.cleaned_data["email"]`, `["password1"]`, `["password2"]` без проверки наличия | `user/forms.py:RegistrationForm.clean` | При ошибке валидации поля — `KeyError`/500 |
| D-12 | Уникальность e‑mail проверяется с учётом регистра (`filter(email=email)`), а вход выполняется по `username=email.lower()`; `email` встроенной модели не уникален | `user/forms.py:RegistrationForm.clean`, `user/views.py:AuthView.post` | Возможна регистрация `A@b.c` и `a@b.c`; для e‑mail в верхнем регистре последующий вход не работает |
| D-13 | Пароль не проверяется `AUTH_PASSWORD_VALIDATORS`, хотя они настроены | `config/settings.py:106-119`, `user/forms.py:RegistrationForm.save` (`create_user` без `validate_password`) | Принимаются любые пароли, включая однозначные/короткие |
| D-14 | Выход реализован через `GET`, без POST и CSRF‑защиты | `user/views.py:LogoutView.get`, `user/urls.py` | Выход можно инициировать сторонним запросом (CSRF на logout) |
| D-15 | При отсутствии аутентификации выполняется редирект на главную, а не на страницу входа | `dashboard/views.py:IsUserAuthenticatedMixin.handle_no_permission` | Пользователь не понимает, почему действие недоступно |
| D-16 | График и внешний API вызываются синхронно внутри HTTP‑запроса без обработки ошибок | `dashboard/views.py:ShareDetailView.get`, `dashboard/services/graph.py:get_graph` | При пустом/неверном `TINKOFF_TOKEN` или недоступности API — 500 на странице детали |
| D-17 | `add_shares` использует `get_or_create` по полному набору атрибутов | `dashboard/management/commands/add_shares.py:Command.handle` | Если у существующей `figi` изменилось любое поле (например, `name`), команда пытается создать дубль и падает на `unique(figi)` |
| D-18 | Секреты и режим отладки заданы небезопасно: пустой `SECRET_KEY`, `DEBUG=True`, пустой `ALLOWED_HOSTS`, креды БД в коде, токен Tinkoff в коде | `config/settings.py:6-10`, `:91-104`, `:134` | Непригодно для эксплуатации в продакшене |
| D-19 | Настройка `AUTH_PASSWORD_VALIDATORS` и `LANGUAGE_CODE="en-us"` не согласованы с русскоязычным интерфейсом | `config/settings.py:106-122`, шаблоны `user/` и `dashboard/` | Смешение языков в интерфейсе и сообщениях |
| D-20 | Тестами покрыты только HTML‑список и CRUD API; регистрация, вход, HTML‑формы, Celery и сервисы не тестируются | `dashboard/tests.py:DashboardTests` | Дефекты D-09…D-13, D-16, D-17 не обнаруживаются |
| D-21 | `ShareListView` не ограничивает объём данных иным способом, кроме пагинации; `ordering` при этом фиксирован и не настраивается пользователем | `dashboard/views.py:ShareListView` | Нет пользовательской сортировки в HTML‑интерфейсе (в отличие от API) |
| D-22 | У `Share` нет связи с пользователем: право на изменение определяется только фактом аутентификации | `dashboard/models.py:Share`, `dashboard/views.py:IsUserAuthenticatedMixin` | Любой зарегистрированный пользователь может менять/удалять любые акции |

---

## 6. Трассировка требований

| Сценарий | Требования |
|---|---|
| UC-01 Просмотр списка | FR-01…FR-08 |
| UC-02 Карточка акции | FR-09…FR-11 |
| UC-03 Регистрация | FR-12…FR-15 |
| UC-04 Вход | FR-16…FR-18 |
| UC-05 Выход | FR-19 |
| UC-06 Создание акции | FR-21…FR-23, FR-27 |
| UC-07 Редактирование | FR-21, FR-24, FR-27 |
| UC-08 Удаление | FR-21, FR-25, FR-26 |
| UC-09 REST API | FR-28…FR-40 |
| UC-10 Фоновое обновление | FR-41…FR-46 |
| UC-11 Импорт справочника | FR-47, FR-48 |
| Администрирование/логирование | FR-49, FR-50 |

---

## 7. Что подтверждено автоматическими тестами

`dashboard/tests.py:DashboardTests` (класс `APITestCase`) проверяет:

- `test_share_list_html` — доступность HTML‑списка (`GET /`, 200) → FR-01;
- `test_share_list` — формат и состав полей списка API → FR-28, FR-38;
- `test_share_detail`, `test_share_detail_invalid` — детальный эндпоинт и 404 → FR-29;
- `test_share_update`, `test_share_update_invalid` — обновление и 400 → FR-31, FR-33;
- `test_share_create`, `test_share_create_invalid` — создание и 400 (с оговоркой D-01) → FR-30, FR-33;
- `test_share_delete`, `test_share_delete_invalid` — удаление и 404 → FR-32.

Не покрыты тестами: регистрация/вход/выход (FR-12…FR-20), HTML‑формы создания/редактирования/удаления (FR-22…FR-27), фильтрация/сортировка/поиск API (FR-35…FR-37), фоновая задача (FR-41…FR-46), импорт (FR-47, FR-48), админка (FR-49).
