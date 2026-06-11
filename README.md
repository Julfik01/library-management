# University Library Management System

System manajemen perpustakaan universitas berbasis web dengan autentikasi JWT, pencarian buku, dan workflow peminjaman/pengembalian.

## Teknologi

| Layer | Stack |
|-------|-------|
| Backend | Python 3.12, FastAPI (async), SQLAlchemy 2.0 (async), Alembic, PyJWT, pwdlib[argon2] |
| Frontend | React 18, Vite, TanStack Query, shadcn/ui, Tailwind CSS, Zod |
| Database | PostgreSQL 16 |
| Auth | JWT access token (in-memory) + httpOnly refresh cookie |

## Fitur (Phase 2)

- **Autentikasi** — Register (student), login, logout, auto-refresh token
- **Katalog Buku** — Pencarian by judul/pengarang/ISBN dengan paginasi
- **Workflow Peminjaman** — Student request → Librarian approve/reject → Librarian record return
- **Admin Buku** — Librarian add/edit/delete buku di katalog
- **RBAC** — 3 role: `student`, `librarian`, `admin_librarian`

## Cara Menjalankan

### Prasyarat
- Docker Desktop

### Langkah

```bash
# 1. Salin file konfigurasi
cp .env.example .env
# Edit .env sesuai kebutuhan

# 2. Jalankan semua service
docker compose up --build

# 3. Akses aplikasi
# Frontend : http://localhost:5173
# Backend  : http://localhost:8000
# API Docs : http://localhost:8000/docs
```

### Akun Default

| Role | Email | Password |
|------|-------|----------|
| admin_librarian | (dari `ADMIN_EMAIL` di `.env`) | (dari `ADMIN_PASSWORD` di `.env`) |

Admin dapat membuat akun librarian lewat halaman **Manage Users**. Student dapat mendaftar sendiri lewat halaman Register.

## Pengembangan

### Struktur Proyek

```
.
├── backend/
│   ├── app/
│   │   ├── models/       # SQLAlchemy ORM models
│   │   ├── routers/      # FastAPI routers (auth, books, borrow, loans, admin)
│   │   ├── schemas/      # Pydantic v2 schemas
│   │   ├── services/     # Business logic
│   │   └── dependencies/ # FastAPI dependencies (auth guards)
│   ├── alembic/          # Database migrations
│   └── tests/            # pytest integration tests
└── frontend/
    └── src/
        ├── components/   # Reusable UI components + AppLayout
        ├── context/      # AuthContext (JWT session management)
        ├── pages/        # Route-level page components
        └── lib/          # axios instance + token interceptors
```

### Menjalankan Tests

Tests membutuhkan PostgreSQL (jalankan via Docker Compose dulu, atau set `TEST_DATABASE_URL`):

```bash
# Dalam container
docker compose exec backend pytest tests/ -v

# Smoke test (SQLite in-memory, tanpa Docker)
docker compose exec backend python tests/test_integration_smoke.py
```

### Environment Variables

| Variable | Deskripsi |
|----------|-----------|
| `POSTGRES_USER` | Username PostgreSQL |
| `POSTGRES_PASSWORD` | Password PostgreSQL |
| `POSTGRES_DB` | Nama database |
| `SECRET_KEY` | Secret untuk JWT (min 32 karakter) |
| `ADMIN_EMAIL` | Email akun admin awal |
| `ADMIN_PASSWORD` | Password akun admin awal |
| `VITE_API_URL` | URL backend untuk frontend (default: `http://localhost:8000`) |

## API Endpoints

| Method | Endpoint | Role | Deskripsi |
|--------|----------|------|-----------|
| POST | `/auth/register` | — | Daftar sebagai student |
| POST | `/auth/login` | — | Login, terima access token + refresh cookie |
| POST | `/auth/refresh` | — | Refresh access token via cookie |
| POST | `/auth/logout` | Auth | Logout, invalidasi refresh token |
| GET | `/books` | Auth | Cari buku (title/author/ISBN, paginated) |
| GET | `/books/{id}` | Auth | Detail satu buku |
| POST | `/admin/books` | librarian, admin | Tambah buku |
| PUT | `/admin/books/{id}` | librarian, admin | Edit buku |
| DELETE | `/admin/books/{id}` | admin | Hapus buku |
| POST | `/borrow` | student | Ajukan permintaan pinjam |
| GET | `/borrow` | Auth | Lihat permintaan (student: milik sendiri; librarian: semua) |
| POST | `/borrow/{id}/approve` | librarian, admin | Setujui permintaan → buat Loan |
| POST | `/borrow/{id}/reject` | librarian, admin | Tolak permintaan |
| GET | `/loans` | Auth | Lihat peminjaman |
| POST | `/loans/{id}/return` | librarian, admin | Catat pengembalian |
| POST | `/admin/users` | admin | Buat akun librarian |

## CI/CD

GitHub Actions (`.github/workflows/ci.yml`) menjalankan:
1. **Backend tests** — pytest dengan PostgreSQL 16 + Python 3.12
2. **Frontend build** — TypeScript type check + Vite build

Trigger: setiap push/PR ke branch `main` atau `develop`.
