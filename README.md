# 📈 Production Stock Market Data Platform

A **production-ready** live data platform for NSE/BSE using Angel One SmartAPI, built with Django + Celery + PostgreSQL on the backend and React on the frontend. It ingests, validates, deduplicates, and streams live market data to dashboards and ML consumers.

---

## 🎯 Features

- **Live data ingestion** every minute via Celery Beat
- **WebSocket streaming** with polling fallback
- **JWT authentication** with encrypted credential storage
- **Reliable pipeline**: validation, deduplication, locking, retries
- **PostgreSQL + Redis** for durability and low-latency cache
- **Modular feature structure** for independent testing and deployment
- **Fetch-only frontend** with error boundaries and retry UI

---

## 🏗️ Architecture

```
Angel One SmartAPI
        |
Django (REST + WS + Celery)
   |            |
PostgreSQL    Redis
   |
React + ML consumers
```

---

## 📁 Project Structure

```
stock/
├── backend/
│   ├── manage.py
│   ├── requirements.txt
│   ├── .env.example
│   ├── config/
│   │   ├── settings/
│   │   ├── asgi.py
│   │   ├── celery.py
│   │   └── urls.py
│   └── features/
│       ├── auth/         # JWT auth + encrypted API credentials
│       ├── stock_data/   # Models, ingestion pipeline, REST API
│       ├── websocket/    # Streaming WebSocket
│       ├── scheduler/    # Redis locks
│       └── ml_engine/    # ML feature entry point
└── frontend/
    ├── package.json
    ├── vite.config.js
    ├── tailwind.config.js
    ├── index.html
    └── src/
        ├── app/          # App shell + routes
        ├── features/     # Feature modules
        └── shared/       # Shared auth + fetch client
```

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **Node.js 18+**
- **Redis Server** (cache + locks)
- **PostgreSQL** (primary DB)
- **Angel One Account** (SmartAPI access)

### 1. Backend Setup

```bash
cd stock/backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env  # Windows
cp .env.example .env    # Linux/Mac
```

### 2. Configure Environment

Edit `backend/.env` and set at least:

```env
DJANGO_SECRET_KEY=your-secret-key
USE_SQLITE=true  # set false and fill DB_* for PostgreSQL
REDIS_HOST=localhost
REDIS_PORT=6379

# Angel One (or store encrypted creds via /auth/angel-one)
ANGEL_ONE_API_KEY=your_api_key
ANGEL_ONE_CLIENT_ID=your_client_id
ANGEL_ONE_PASSWORD=your_password
ANGEL_ONE_TOTP_SECRET=your_totp_secret

# Encryption key for stored credentials
CREDENTIAL_ENCRYPTION_KEY=your_fernet_key

# Symbols to ingest
STOCK_TOKEN_MAP=[{"symbol":"RELIANCE","token":"2885","exchange":"NSE"}]
```

### 3. Migrate + Create User

```bash
python manage.py migrate
python manage.py createsuperuser
```

### 4. Run Backend + Celery

```bash
python manage.py runserver
celery -A config.celery worker -l info
celery -A config.celery beat -l info
```

### 5. Frontend Setup

```bash
cd stock/frontend
npm install
npm run dev
```

### 6. Access Dashboard

Open **http://localhost:5173**

---

## 🔧 Configuration

### Backend Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `DJANGO_SECRET_KEY` | Django secret | Required |
| `DB_NAME` | PostgreSQL database name | Required if USE_SQLITE=false |
| `CREDENTIAL_ENCRYPTION_KEY` | Fernet key | Required for encrypted creds |
| `STOCK_TOKEN_MAP` | Instruments to ingest | Required |
| `STOCK_POLL_INTERVAL_SECONDS` | Ingestion interval | `60` |

Optional `frontend/.env`:

```env
VITE_API_BASE_URL=http://localhost:8000
```

---

## 📡 API Endpoints

### Auth

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/auth/login/` | Obtain JWT access/refresh tokens |
| POST | `/auth/refresh/` | Refresh access token |
| POST | `/auth/logout/` | Blacklist refresh token |
| PUT | `/auth/angel-one/` | Store encrypted SmartAPI credentials |

### Stock Data (REST)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/stocks/latest/` | Latest price snapshot (auth required) |
| GET | `/stocks/history/?symbol=RELIANCE` | Historical prices |

### WebSocket

| Endpoint | Description |
|----------|-------------|
| `ws://localhost:8000/stocks/stream/?token=JWT` | Live price stream |

---

## ✅ Data Reliability

- Validate all incoming data (numeric checks, high >= low, non-negative)
- Normalize timestamps to minute-level buckets
- Deduplicate with a unique `(symbol, timestamp)` constraint
- Redis locks prevent overlapping ingestion jobs
- Retries with exponential backoff in Celery

---

## 🧪 Development

```bash
# Backend tests
cd backend
python manage.py test

# Frontend lint
cd frontend
npm run lint
```

---

## 🚀 Production Deployment

### Backend

1. Set `DEBUG=False`
2. Configure `ALLOWED_HOSTS`
3. Run ASGI server:

```bash
uvicorn config.asgi:application --host 0.0.0.0 --port 8000
```

### Nginx (example)

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        root /path/to/frontend/dist;
        try_files $uri $uri/ /index.html;
    }

    location /stocks/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /auth/ {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /stocks/stream/ {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

---

## 🔒 Security Notes

- Never commit `.env`
- Use `CREDENTIAL_ENCRYPTION_KEY` for stored API secrets
- Enforce HTTPS in production
- Rotate API credentials regularly
