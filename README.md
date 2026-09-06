# Peblo TV Mini

A full-stack mini streaming platform consisting of a content management system (CMS), publishing pipeline, API, and public catalogue viewer.

The application demonstrates content management, artwork validation, role-based access control, catalogue generation, language-variant grouping, search/filtering, and a separate public viewing experience.

---

## Tech Stack

### Backend
- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- JWT Authentication
- Pillow for image validation

### Frontend
- React
- TypeScript
- Vite
- React Router

### Storage
- Local filesystem storage through a storage abstraction
- Designed so the storage implementation can be replaced with MinIO or Cloudflare R2

---

## Architecture

```text
                    ┌──────────────────┐
                    │    React CMS     │
                    │   /cms           │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │    FastAPI API   │
                    │   REST Endpoints │
                    └────────┬─────────┘
                             │
                 ┌───────────┴───────────┐
                 ▼                       ▼
        ┌─────────────────┐     ┌─────────────────┐
        │   PostgreSQL    │     │ Artwork Storage │
        │ Shows/Seasons/  │     │ Poster/Banner/  │
        │ Episodes/etc.   │     │ Thumbnail       │
        └─────────────────┘     └─────────────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │ Publish Service  │
                    │ catalogue.json   │
                    └────────┬─────────┘
                             │
                             ▼
                    ┌──────────────────┐
                    │  React Viewer    │
                    │      /           │
                    └──────────────────┘
