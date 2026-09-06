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

The CMS communicates with the FastAPI backend.

The backend stores structured content in PostgreSQL and artwork through the storage layer.

When an administrator publishes the catalogue, the backend generates a published catalogue snapshot.

The public viewer consumes this published catalogue and does not use administrative APIs.

3. Core Features
3.1 Content Management System

The CMS provides functionality for managing:

Shows
Seasons
Episodes
Artwork
Publishing status
Validation issues

The CMS also provides:

Search
Filtering
Content management
Validation reporting
Publishing controls
Publish history
Role-based access
4. Authentication and Authorization

The application implements JWT-based authentication with two roles:

Admin

Admins can:

Log in
View content
Create shows
Update shows
Delete shows
Manage seasons
Manage episodes
Upload artwork
View validation reports
Publish the catalogue
Editor

Editors can:

Log in
View CMS content
Create and update content
Manage shows
Manage seasons
Manage episodes
Upload artwork
View validation information

Editors cannot publish the catalogue.

Publishing permissions are enforced by the backend API rather than relying only on frontend UI controls.

This prevents an editor from bypassing the UI and directly calling the publish endpoint.

5. Demo Credentials

For local evaluation:

Admin
Username: admin
Password: admin123
Editor
Username: editor
Password: editor123

These credentials are intended only for local assessment/demo purposes.

For a production deployment, credentials and JWT secrets should be provided through environment variables or a dedicated secrets manager.

6. Artwork Management

Artwork is validated on the server before being stored.

The application supports three artwork types.

Artwork Type	Required Dimensions	Maximum File Size
Poster	600 × 900 px	200 KB
Banner	1280 × 720 px	200 KB
Thumbnail	640 × 360 px	200 KB

The backend checks:

File type
File size
Image dimensions
Artwork type
Target content
Existing artwork

Invalid files are rejected with human-readable error messages.

Example:

Poster must be 600x900px. Received 900x600px.

Files larger than 200 KB are rejected.

Existing artwork is not silently overwritten.

7. Artwork Storage Decision

For the assessment, artwork is stored using the local filesystem.

The storage logic is kept behind an abstraction so that the storage implementation can be replaced without changing the higher-level application workflow.

Possible production implementations include:

Cloudflare R2
MinIO
S3-compatible object storage
Why local storage?

The assessment is intended to be easy to run locally without requiring cloud credentials.

Trade-off

Local filesystem storage is not ideal for horizontally scaled production deployments because multiple application instances would not automatically share the same files.

For production, object storage would be preferred.

8. Database Model

The application uses a relational PostgreSQL model.

The main entities are:

Shows
  │
  └── Seasons
        │
        └── Episodes

Shows ─────── Artwork
Episodes ──── Artwork

Publish Runs

The model supports:

Shows
Seasons
Episodes
Artwork records
Validation issues
Publish runs

Alembic is used to manage database migrations.

9. Episode Constraints

The application enforces important content rules.

An episode cannot be published without:

Required artwork
Duration

Episode language variants are uniquely identified using:

(content_group, language)

This prevents duplicate language records for the same content group.

10. Language Variant Handling

The seed data contains episodes where multiple records represent different language versions of the same content.

Episodes sharing the same content_group are therefore treated as language variants.

For example:

Content Group:
motis-many-lives-s01e02

Languages:
- English
- Hindi

Instead of displaying duplicate episodes in the viewer, the publishing process groups the language variants into one catalogue entry.

The catalogue retains the available languages and variant information.

Decision

Grouping is performed during catalogue generation rather than duplicating the same content in the viewer.

Trade-off

The published catalogue structure is slightly more complex, but the viewer experience is cleaner and avoids duplicate episodes.

11. Season 0 Handling

Season 0 is reserved for trailers/promotional content.

Season 0 records are retained in the backend but are not shown as a normal season in the public viewer.

This follows the challenge convention that Season 0 should not behave like a standard viewer season.

12. Validation Report

The CMS provides a validation report before publishing.

Validation identifies issues such as:

Missing artwork
Missing duration
Missing show section
Duplicate language/content combinations
Other catalogue consistency problems

Issues are classified as:

Blocking issues
Warnings

This allows editors to understand what must be fixed before publishing.

The validation report is exposed through:

GET /admin/validation-report
13. Catalogue Publishing

Publishing is one of the main parts of the application.

The publishing process:

CMS
 ↓
Validation
 ↓
Select eligible content
 ↓
Group language variants
 ↓
Deterministic ordering
 ↓
Generate catalogue snapshot
 ↓
Record publish run
 ↓
Public Viewer

Only eligible published content is included.

Draft content is excluded.

The publishing process also:

Validates required content
Groups language variants
Applies deterministic ordering
Generates a catalogue snapshot
Records publish information
Provides a catalogue version
14. Publish Reliability

The viewer should not expose partially generated catalogue data.

The application therefore treats the published catalogue as a snapshot.

If a new publish operation fails, the previously valid published catalogue remains available rather than exposing incomplete content.

This creates a clear boundary between:

Draft/Admin Data

and

Published Viewer Data
15. Why Use a Published Catalogue?

The viewer does not directly query the administrative database for every page.

Instead:

PostgreSQL
    ↓
Publish Process
    ↓
Published Catalogue
    ↓
Viewer
Advantages
Public viewer is separated from admin operations.
The viewer has a stable published state.
Unpublished changes do not accidentally appear publicly.
Catalogue delivery can be cached or served efficiently.
Failed publishing does not expose partially generated data.
Trade-off

Editors must publish changes before they become visible to viewers.

For a larger production system, the catalogue could be stored in object storage/CDN infrastructure and versioned more extensively.

16. Public Catalogue API

The public catalogue endpoint is:

GET /catalog

It returns the currently published catalogue.

The viewer uses this endpoint rather than admin APIs.

17. Search and Filtering

The application provides:

GET /catalog/search

Search supports:

Show title
Episode title
Category

Filtering supports:

Category
Language
Section

Filters can be combined.

Example:

/catalog/search?q=moti&category=india&language=hi
Current implementation decision

The assessment dataset is relatively small, so API-level filtering is sufficient and keeps the implementation simple.

Scaling trade-off

For a much larger catalogue, search should be moved toward:

PostgreSQL indexes
PostgreSQL full-text search
Search-specific indexes
Dedicated search services such as Elasticsearch/OpenSearch

This would avoid repeatedly scanning large datasets in application code.

18. Viewer Application

The viewer is available at:

/

The viewer includes:

Featured/hero content
Banner artwork
Poster-based show rows
Episode information
Episode duration
Language variants
Search
Category filtering
Language filtering
Show details
Season navigation

Only published catalogue content is displayed.

Draft CMS content is never directly exposed through the viewer.

19. CMS Application

The CMS is available at:

/cms

The CMS includes:

Login
Dashboard
Show listing
Search
Content management
Validation report
Artwork upload
Publish controls
Publish history
20. API Endpoints
Authentication
POST /auth/login
GET  /auth/me
Public Catalogue
GET /catalog
GET /catalog/search
Shows
GET    /admin/shows
POST   /admin/shows
GET    /admin/shows/{id}
PUT    /admin/shows/{id}
DELETE /admin/shows/{id}
Validation
GET /admin/validation-report
Publishing
POST /admin/catalog/publish
Artwork
POST /admin/artwork/upload

The backend protects administrative endpoints using JWT authentication and role checks.

21. API Documentation

FastAPI automatically provides interactive API documentation.

After starting the backend, open:

http://127.0.0.1:8000/docs

This can be used to inspect and test the API endpoints.

22. How to Run Locally
Prerequisites

Install:

Python 3.10+
Node.js 18+
PostgreSQL 14+
Git

Docker can also be used for the PostgreSQL development database.

Step 1: Clone the Repository
git clone https://github.com/Kavitha-89/peblo-tv-mini.git
cd peblo-tv-mini
Step 2: Start PostgreSQL

Make sure PostgreSQL is running.

The application expects the database connection configured in the backend environment.

Example development database:

Database: peblo_tv
User: peblo
Password: peblo123
Host: localhost
Port: 5433

Adjust these values if your local PostgreSQL configuration is different.

Step 3: Set Up Backend
cd backend

Create and activate a virtual environment if desired:

Windows
python -m venv venv
venv\Scripts\activate
macOS/Linux
python3 -m venv venv
source venv/bin/activate

Install dependencies:

pip install -r requirements.txt
Step 4: Run Database Migrations

From the backend directory:

alembic upgrade head

This creates/updates the required PostgreSQL tables.

Step 5: Start FastAPI
uvicorn main:app --reload

The API will be available at:

http://127.0.0.1:8000

Swagger documentation:

http://127.0.0.1:8000/docs
23. Run the Frontend

Open a second terminal.

cd frontend

Install dependencies:

npm install

Start the development server:

npm run dev

Vite will display the local frontend URL in the terminal.

The main routes are:

/       → Public Viewer
/cms    → CMS
24. Production Build

To verify the frontend production build:

cd frontend
npm run build

The generated production files are placed in:

frontend/dist
25. Project Structure
peblo-tv-mini/
│
├── backend/
│   ├── main.py
│   ├── auth.py
│   ├── database.py
│   ├── models.py
│   ├── schemas.py
│   ├── migrations/
│   │   └── versions/
│   └── assets/
│       ├── poster/
│       ├── banner/
│       └── thumbnail/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── types/
│   ├── package.json
│   └── vite.config.ts
│
├── seed_shows.json
├── reference.json
└── README.md
26. Testing

The important application paths were tested during development.

Authentication

Tested:

Admin login
Editor login
Authentication token validation
/auth/me
Authorization

Tested:

Admin access
Editor CRUD access
Editor publish restriction
Backend role enforcement
Artwork

Tested:

Valid poster
Invalid poster dimensions
Valid banner
Invalid banner dimensions
Valid thumbnail
Invalid thumbnail dimensions
File-size validation
Duplicate artwork protection
Publishing

Tested:

Validation report
Published content selection
Draft content exclusion
Catalogue generation
Publish history
Language variant grouping
Search

Tested:

Search by title
Category filtering
Language filtering
Combined filters
Viewer

Tested:

Published shows
Draft show exclusion
Season 0 hiding
Language variants
Episode information
Artwork rendering
27. Seed Data Handling

The supplied seed data intentionally contains imperfect records.

The application does not blindly assume that every record is valid.

Examples of issues identified during development include:

Published episode without artwork
Duplicate (content_group, language) data
Draft content without a section

These issues are surfaced through validation rather than silently ignored.

This allows the CMS/editor workflow to identify problems before publication.

28. Technical Decisions
FastAPI

FastAPI was selected because:

It provides automatic OpenAPI documentation.
It has strong request/response validation.
Dependency injection makes authentication checks straightforward.
It is lightweight and suitable for a small API service.
Trade-off

For a larger production backend, the project would benefit from additional service-layer separation, background workers, structured logging, and observability.

PostgreSQL

PostgreSQL was selected because the content model is relational.

Shows contain seasons, seasons contain episodes, and artwork and publish runs have relationships with the content.

Trade-off

A relational database requires schema management and migrations, but provides strong consistency, relationships, and constraints.

SQLAlchemy

SQLAlchemy was used as the ORM/database layer.

Reason

It keeps database operations structured and makes the relationship between the Python domain model and PostgreSQL schema explicit.

Alembic

Alembic is used for database migrations.

Reason

Schema changes should be reproducible instead of requiring manual database modifications.

React + TypeScript

React and TypeScript were selected for the CMS and viewer.

Reason

React supports component-based UI development, while TypeScript provides compile-time type checking for catalogue/API structures.

JWT Authentication

JWT was selected for the assessment because it provides a simple stateless authentication mechanism.

Production improvement

A production system would use:

Secure secret management
Refresh token strategy
Password hashing
Token rotation
Rate limiting
Potential external identity provider
29. Important Trade-offs

The implementation intentionally prioritizes correctness and clarity of the core publishing workflow over production-scale infrastructure.

Local storage vs cloud storage

Local storage was selected to simplify evaluation.

Trade-off: it does not scale across multiple backend instances.

Application-level search vs search engine

Application/API-level filtering is sufficient for the supplied dataset.

Trade-off: larger datasets should use database indexes/full-text search or a dedicated search service.

Published catalogue vs live database queries

A published snapshot provides a stable public experience.

Trade-off: changes require another publish operation.

JWT vs external authentication

JWT keeps the assessment self-contained.

Trade-off: production authentication would require stronger security controls.

30. Security Considerations

The application enforces authorization at the backend.

Frontend controls are treated as UI convenience rather than the security boundary.

Production improvements would include:

Secrets stored outside source code
Strong password hashing
HTTPS
Token expiration and refresh strategy
Rate limiting
Secure cookie/token strategy
Database credentials stored in secrets
Object storage credentials stored in secrets
Audit logging
Security monitoring

The credentials included in this README are demo credentials only.

31. Reliability and Failure Handling

A key design goal is avoiding partially published catalogue data.

The publishing process creates a complete catalogue snapshot.

The viewer consumes the last successful published state.

This means:

New publish succeeds
        ↓
New catalogue becomes available

New publish fails
        ↓
Previous published catalogue remains available

This is preferable to directly exposing partially generated content.

32. Production Deployment Considerations

A production deployment could use:

React CMS
     │
     ▼
Load Balancer
     │
     ▼
FastAPI Application
     │
 ┌───┴───────────┐
 ▼               ▼
PostgreSQL    Object Storage
                  │
                  ▼
              CDN/R2
                  │
                  ▼
              Viewer

Recommended production changes:

Cloud-managed PostgreSQL
Cloudflare R2/S3-compatible artwork storage
CDN for static artwork
HTTPS
Environment-based configuration
Secret manager
Database backups
Monitoring
Structured logs
Background publishing jobs
Automated tests
CI/CD
33. Scaling Search

The current implementation is designed for the supplied assessment dataset.

For larger catalogues, the next step would be to introduce:

PostgreSQL indexes for frequently filtered fields.
PostgreSQL full-text search for title/category queries.
Pagination at the API/database level.
Search result caching where useful.
A dedicated search engine if catalogue size and query complexity justify it.

This avoids scaling problems from loading and filtering the entire catalogue in application memory.

34. Possible Future Improvements

The following features were considered but are outside the core implementation scope:

Versioned catalogue rollback
Publish dry-run/diff
Complete audit log
Background publishing queue
Dedicated search service
Cloud object storage integration
Automated end-to-end browser tests
Advanced media processing
CDN integration
Production-grade identity provider integration
35. Known Limitations / Omissions

The assessment prioritised the core CMS, API, validation, publishing, and viewer workflows.

Known areas for further development include:

Production object storage
More extensive automated integration tests
Production secret management
Advanced authentication lifecycle
Dedicated search infrastructure
Background job processing
Full audit logging
Catalogue rollback
Dry-run publishing diff
Complete CI/CD deployment infrastructure

These can be added without fundamentally changing the core content model or viewer/publishing architecture.
