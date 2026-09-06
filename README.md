\# Peblo TV Mini



A full-stack mini streaming CMS and catalogue application built as part of the Peblo TV Mini challenge.



\## Tech Stack



\- Backend: Python, FastAPI, SQLAlchemy, PostgreSQL

\- Frontend: React, TypeScript, Vite

\- Authentication: JWT with Admin and Editor roles

\- Storage: Local artwork storage abstraction

\- Database migrations: Alembic



\## Features



\### Admin CMS



\- Admin and Editor authentication

\- Show, season and episode management

\- Artwork upload with validation

\- Poster: 600 × 900 px

\- Banner: 1280 × 720 px

\- Thumbnail: 640 × 360 px

\- Maximum artwork size: 200 KB

\- Validation report for content issues

\- Role-based permissions

\- Catalogue publishing with publish history



\### Catalogue



\- Publishes only valid published content

\- Groups language variants using `content\_group`

\- Deterministic catalogue generation

\- Atomic catalogue publishing

\- Published catalogue versioning

\- Search by show title, episode title and category

\- Category and language filters



\### Viewer



\- Separate public viewer interface

\- Netflix-style catalogue layout

\- Featured/banner artwork

\- Poster-based show rows

\- Episode information and durations

\- Language variants

\- Season 0 trailers are hidden from normal seasons

\- Search and filtering



\## API Endpoints



\### Public



\- `GET /catalog`

\- `GET /catalog/search`



\### Admin



\- `POST /auth/login`

\- `GET /auth/me`

\- `GET /admin/shows`

\- `POST /admin/shows`

\- `PUT /admin/shows/{id}`

\- `DELETE /admin/shows/{id}`

\- `GET /admin/validation-report`

\- `POST /admin/catalog/publish`

\- `POST /admin/artwork/upload`



\## Demo Credentials



For local demonstration:



\*\*Admin\*\*

\- Username: `admin`

\- Password: `admin123`



\*\*Editor\*\*

\- Username: `editor`

\- Password: `editor123`



These credentials and the demo JWT secret are intended only for local evaluation and should be moved to environment variables in production.



\## Running Locally



\### Backend



```bash

cd backend

pip install -r requirements.txt

uvicorn main:app --reload





API:

http://127.0.0.1:8000



API documentation:

http://127.0.0.1:8000/docs



Frontend

cd frontend

npm install

npm run dev



The application provides:



/ — Public Viewer

/cms — CMS

Architecture

React CMS

&#x20;   |

&#x20;   v

FastAPI API

&#x20;   |

&#x20;   +---- PostgreSQL

&#x20;   |

&#x20;   +---- Artwork Storage

&#x20;   |

&#x20;   v

Publish Service

&#x20;   |

&#x20;   v

Published Catalogue

&#x20;   |

&#x20;   v

React Viewer



The viewer consumes the published catalogue rather than admin APIs. This keeps the public experience independent from CMS operations.



Validation and Publishing



Content validation is performed before publishing. Artwork dimensions, file size, required metadata, publishing status and other content rules are checked.



Publishing creates a new catalogue snapshot containing only eligible published content. Language variants sharing the same content\_group are represented together.



Production Considerations



For production deployment, secrets should be provided through environment variables or a secrets manager. Local artwork storage can be replaced with object storage such as Cloudflare R2 or MinIO without changing the application-level storage interface.



For a larger catalogue, search can be moved from application-level filtering to PostgreSQL indexes/full-text search or a dedicated search service.



AI Usage



AI assistance was used during development for debugging, implementation guidance and reviewing edge cases. Final implementation decisions, testing and integration were performed manually.





\### Now add it



From your current PowerShell:

```powershell

notepad README.md

