# Investing Demo

Учебное Django-приложение для просмотра акций, истории цен и управления
справочником инструментов. Рыночные данные поступают из Tinkoff Invest API,
фоновая задача Celery периодически обновляет последние цены.

## Стек

- Python 3.12+ (проверено на 3.14)
- Django 6.1, Django REST Framework 3.18, django-filter
- Celery 5.6 + Redis (брокер)
- PostgreSQL 17 или SQLite (локальная разработка)
- plotly (графики), django-crispy-forms + Bootstrap 5
- Tinkoff Invest SDK (опционально, для рыночных данных)

## Быстрый запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# при необходимости отредактируйте .env (TINKOFF_TOKEN и др.)

python manage.py migrate
python manage.py createsuperuser   # по желанию, для /admin/
python manage.py runserver
```

Приложение будет доступно на <http://127.0.0.1:8000/>.
По умолчанию используется SQLite (`db.sqlite3`), поэтому PostgreSQL для
локального запуска не обязателен.

### PostgreSQL

```bash
docker compose up -d db
export DB_ENGINE=postgres
python manage.py migrate
```

Параметры подключения задаются переменными `POSTGRES_*` (см. `.env.example`).

### Tinkoff Invest API

Пакет `tinkoff-investments` больше не устанавливается с PyPI (проект находится
в карантине). SDK ставится из официального репозитория:

```bash
pip install -r requirements-optional.txt
pip install --no-deps "git+https://github.com/RussianInvestments/invest-python.git@fcf0af1e27f053cd4bc75eb20863ece23a202d47"
```

Укажите `TINKOFF_TOKEN` в `.env`. Без токена приложение запускается, но график
на странице акции не отображается, а команда `add_shares` и задача обновления
цен сообщают об отсутствии данных.

### Импорт справочника акций

```bash
python manage.py add_shares
```

Команда обновляет существующие записи по `figi` и создаёт новые.

### Celery

```bash
celery -A config worker -l info
celery -A config beat -l info
```

Расписание: обновление цен каждые 5 минут (`config/celery.py`).
Для локальной проверки задачи без брокера можно установить
`CELERY_TASK_ALWAYS_EAGER=true`.

## История рыночных цен

При каждом успешном обновлении цен задача `update_last_price` сохраняет снимок
в `PriceHistory`: цену и время котировки. Повторная котировка с тем же
`(акция, время)` не создаёт дубль.

Страница истории доступна по адресу `/history/<id>` (ссылка есть на странице
акции):

- периоды 7, 30, 90, 180 и 365 дней;
- первая/последняя/минимальная/максимальная цена;
- абсолютное и процентное изменение за период;
- график по накопленным в БД точкам (ряд прореживается до 500 точек);
- 20 последних снимков за выбранный период.

История накапливается по мере работы Celery. Без `TINKOFF_TOKEN` страница
открывается, но показывает сообщение об отсутствии данных. Снимки также
доступны в админке Django. Подробности — в `NEW_FEATURE.md`.

## Тесты

```bash
python manage.py test
```

или с отчётом о покрытии:

```bash
coverage run manage.py test
coverage report
```

Линтинг:

```bash
pip install -r requirements-dev.txt
ruff check .
```

## Аутентификация

- регистрация: `/user/registration/`;
- вход: `/user/login/`;
- выход: POST-форма на `/user/logout/` (GET возвращает 405 — защита от CSRF).

## API

- `GET /api/v1/shares/` — список (пагинация `limit`/`offset`, фильтры
  `name`/`ticker`, сортировка `ordering`, поиск `search`);
- `GET /api/v1/shares/<id>/` — одна акция;
- `POST /api/v1/shares/`, `PUT/PATCH /api/v1/shares/<id>/`,
  `DELETE /api/v1/shares/<id>/` — изменение справочника.

По умолчанию API открыт, как и в исходной версии. Чтобы требовать
аутентификацию для изменения данных, установите `API_REQUIRE_AUTH=true`.

## Структура проекта

```
config/       настройки, URL, WSGI/ASGI, Celery
dashboard/    акции: модели, HTML-представления, REST API, сервисы, задачи
user/         регистрация, вход и выход
```
