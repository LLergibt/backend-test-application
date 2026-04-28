# Effective Mobile application



---

## Запуск проекта
Для запуска потребуется docker, docker compose

### Docker Compose

```bash
cp .env.example .env # Использовать свои данные в .env
docker compose up --build -d
docker compose exec app python seed.py # Тестовые данные
```


Документация Swagger: **http://localhost:8000/docs**

---

## Структура проекта

```
project/
├── app/
│   ├── main.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── models/
│   │   ├── user.py
│   │   ├── rbac.py
│   │   └── token_blacklist.py
│   ├── schemas/
│   │   ├── user.py
│   │   └── auth.py
│   ├── routers/
│   │   ├── auth.py
│   │   └── users.py
│   ├── dependencies/
│   │   └── auth.py
│   └── services/
│       └── user_service.py
├── seed.py                      # заполнение тестовыми данными
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Система разграничения прав доступа


```
Пользователь (User)
     │
     │  many-to-many (UserRole)
     ▼
   Роль (Role)
     │
     │  many-to-many (RolePermission)
     ▼
Разрешение (Permission)
```

- Каждый пользователь может иметь **одну или несколько ролей**.
- Каждая роль содержит **набор атомарных разрешений**.
- Разрешения имеют формат `ресурс:действие` (например, `users:read_all`).
- Проверка прав выполняется через dependency `require_permission("permission_name")` или через вспомогательную функцию `_check_permission()` внутри роутера.

### Таблицы БД

| Таблица            | Назначение                           |
| ------------------ | ------------------------------------ |
| `users`            | Аккаунты пользователей               |
| `roles`            | Роли (admin, moderator, user)        |
| `permissions`      | Права доступа                        |
| `role_permissions` | Роль - Разрешение (many-to-many)     |
| `user_roles`       | Пользователь - Роль (many-to-many)   |
| `token_blacklist`  | Инвалидированные JWT-токены (logout) |

### Разрешения (Permissions)

| Разрешение          | Описание                                 |
|---------------------|------------------------------------------|
| `users:read_all`    | Просмотр профиля любого пользователя     |
| `users:read_own`    | Просмотр собственного профиля            |
| `users:update_all`  | Редактирование профиля любого пользователя |
| `users:update_own`  | Редактирование собственного профиля      |
| `users:delete_all`  | Мягкое удаление любого пользователя      |
| `users:delete_own`  | Мягкое удаление собственного аккаунта    |

### Роли и их права

| Роль        | Разрешения                                                                                   |
|-------------|----------------------------------------------------------------------------------------------|
| `admin`     | ВСЕ разрешения                                                                               |
| `moderator` | `users:read_all`, `users:read_own`, `users:update_own`, `users:delete_own`                  |
| `user`      | `users:read_own`, `users:update_own`, `users:delete_own`                                    |

### Матрица доступа к эндпоинтам

| Эндпоинт              | Метод  | `user` | `moderator` | `admin` | Не аутентиф. |
| --------------------- | ------ | ------ | ----------- | ------- | ------------ |
| `/auth/register`      | POST   | 201    | 201         | 201     | 201          |
| `/auth/login`         | POST   | 201    | 201         | 201     | 201          |
| `/auth/logout`        | POST   | 201    | 201         | 201     | 401          |
| `/auth/me`            | GET    | 200    | 200         | 200     | 401          |
| `/users`              | GET    | 403    | 200         | 200     | 401          |
| `/users/{id}` (свой)  | GET    | 200    | 200         | 200     | 401          |
| `/users/{id}` (чужой) | GET    | 403    | 200         | 200     | 401          |
| `/users/{id}` (свой)  | PATCH  | 200    | 200         | 200     | 401          |
| `/users/{id}` (чужой) | PATCH  | 403    | 403         | 200     | 401          |
| `/users/{id}` (свой)  | DELETE | 200    | 200         | 200     | 401          |
| `/users/{id}` (чужой) | DELETE | 403    | 403         | 200     | 401          |

### Мягкое удаление (soft delete)

При удалении аккаунта:
1. `is_active` выставляется в `False` (запись остаётся в БД).
2. Пользователь должен сам выйти (вызвать `/auth/logout`).
3. При попытке входа деактивированный аккаунт получает `401 Unauthorized`.
4. Текущий JWT остаётся валидным до logout или истечения TTL.

### Аутентификация через JWT

- После успешного логина клиент получает **Bearer JWT**.
- Токен передаётся в заголовке `Authorization: Bearer <token>`.
- При logout токен помещается в `token_blacklist` и более не принимается.

---

## Эндпоинты API

### Auth

```
POST  /auth/register    - регистрация нового пользователя
POST  /auth/login       - вход (возвращает JWT)
POST  /auth/logout      - выход (инвалидирует токен)
GET   /auth/me          - профиль текущего пользователя
```

### Users

```
GET    /users            - список всех пользователей  [users:read_all]
GET    /users/{id}       - профиль пользователя
PATCH  /users/{id}       - обновить профиль
DELETE /users/{id}       - мягкое удаление
```

---

## Тестовые данные

После запуска `python seed.py`:

| Email                 | Пароль    | Роль      | Активен  |
| --------------------- | --------- | --------- | -------- |
| admin@example.com     | Admin1234 | admin     | active   |
| moderator@example.com | Moder1234 | moderator | active   |
| alice@example.com     | Alice1234 | user      | active   |
| bob@example.com       | Bob12345  | user      | inactive |

---

## Переменные окружения

| Переменная                    | Описание                    | По умолчанию               |
| ----------------------------- | --------------------------- | -------------------------- |
| `DATABASE_URL`                | URL подключения к Postgres  | `postgresql+asyncpg://...` |
| `SECRET_KEY`                  | Секрет для подписи JWT      | `secret_key...`            |
| `ALGORITHM`                   | Алгоритм JWT                | `HS256`                    |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Время жизни токена (минуты) | `60`                       |

## Выключение контейнеров(с удалением данных)
```bash
docker compose down -v
```
