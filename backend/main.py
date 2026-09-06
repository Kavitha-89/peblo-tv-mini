from pathlib import Path

from fastapi import (
    FastAPI,
    Depends,
    HTTPException,
    UploadFile,
    File,
    Query,
)

from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import Base, engine, SessionLocal
from models import (
    Show,
    ShowCategory,
    Season,
    Episode,
    Artwork,
    PublishRun,
    ValidationIssue,
)
from artwork import validate_artwork
from validation import validate_database
from catalogue import (
    build_catalogue,
    write_catalogue_atomically,
    read_catalogue,
)
from auth import (
    authenticate_user,
    create_access_token,
    require_editor_or_admin,
    require_admin,
)


# ---------------------------------------------------------
# Application setup
# ---------------------------------------------------------

app = FastAPI(
    title="Peblo TV Mini API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
BASE_DIR = Path(__file__).resolve().parent
ASSETS_DIR = BASE_DIR / "assets"

ASSETS_DIR.mkdir(parents=True, exist_ok=True)

app.mount(
    "/assets",
    StaticFiles(directory=str(ASSETS_DIR)),
    name="assets",
)

Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------
# Database dependency
# ---------------------------------------------------------

def get_db():
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------

class LoginRequest(BaseModel):
    username: str
    password: str


class ShowCreate(BaseModel):
    slug: str
    title: str
    description: str | None = None
    section: str | None = None
    status: str = "draft"
    categories: list[str] = []


class ShowUpdate(BaseModel):
    slug: str | None = None
    title: str | None = None
    description: str | None = None
    section: str | None = None
    status: str | None = None
    categories: list[str] | None = None


class SeasonCreate(BaseModel):
    show_id: int
    season_number: int
    title: str | None = None


class SeasonUpdate(BaseModel):
    season_number: int | None = None
    title: str | None = None


class EpisodeCreate(BaseModel):
    season_id: int
    episode_number: int
    title: str
    description: str | None = None
    duration: int | None = None
    language: str
    content_group: str
    status: str = "draft"


class EpisodeUpdate(BaseModel):
    season_id: int | None = None
    episode_number: int | None = None
    title: str | None = None
    description: str | None = None
    duration: int | None = None
    language: str | None = None
    content_group: str | None = None
    status: str | None = None


# ---------------------------------------------------------
# Helper functions
# ---------------------------------------------------------

def serialize_show(show: Show):
    return {
        "id": show.id,
        "slug": show.slug,
        "title": show.title,
        "description": show.description,
        "section": show.section,
        "status": show.status,
        "categories": [
            category.category
            for category in show.categories
        ],
    }


def serialize_season(season: Season):
    return {
        "id": season.id,
        "show_id": season.show_id,
        "season_number": season.season_number,
        "title": season.title,
    }


def serialize_episode(episode: Episode):
    return {
        "id": episode.id,
        "seed_episode_id": episode.seed_episode_id,
        "season_id": episode.season_id,
        "episode_number": episode.episode_number,
        "title": episode.title,
        "description": episode.description,
        "duration": episode.duration,
        "language": episode.language,
        "content_group": episode.content_group,
        "status": episode.status,
    }


def serialize_artwork(artwork: Artwork):
    return {
        "id": artwork.id,
        "episode_id": artwork.episode_id,
        "show_id": artwork.show_id,
        "artwork_type": artwork.artwork_type,
        "file_path": artwork.file_path,
        "width": artwork.width,
        "height": artwork.height,
        "size_bytes": artwork.file_size,
    }


# ---------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------

@app.post("/auth/login")
def login(payload: LoginRequest):
    user = authenticate_user(
        payload.username,
        payload.password,
    )

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Invalid username or password.",
        )

    access_token = create_access_token(
        user["username"],
        user["role"],
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": user["username"],
        "role": user["role"],
    }


@app.get("/auth/me")
def get_me(
    current_user=Depends(require_editor_or_admin),
):
    return current_user


# ---------------------------------------------------------
# Health
# ---------------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "peblo-tv-mini-api",
    }


# =========================================================
# SHOW CRUD
# =========================================================

@app.get("/admin/shows")
def get_shows(
    db: Session = Depends(get_db),
    current_user=Depends(require_editor_or_admin),
):
    shows = (
        db.query(Show)
        .order_by(Show.id)
        .all()
    )

    return [
        serialize_show(show)
        for show in shows
    ]


@app.post("/admin/shows")
def create_show(
    payload: ShowCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_editor_or_admin),
):
    existing = (
        db.query(Show)
        .filter(Show.slug == payload.slug)
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="A show with this slug already exists.",
        )

    show = Show(
        slug=payload.slug,
        title=payload.title,
        description=payload.description,
        section=payload.section,
        status=payload.status,
    )

    db.add(show)
    db.flush()

    for category in payload.categories:
        show.categories.append(
            ShowCategory(category=category)
        )

    db.commit()
    db.refresh(show)

    return serialize_show(show)


@app.put("/admin/shows/{show_id}")
def update_show(
    show_id: int,
    payload: ShowUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_editor_or_admin),
):
    show = (
        db.query(Show)
        .filter(Show.id == show_id)
        .first()
    )

    if not show:
        raise HTTPException(
            status_code=404,
            detail="Show not found.",
        )

    if payload.slug is not None:
        existing = (
            db.query(Show)
            .filter(
                Show.slug == payload.slug,
                Show.id != show_id,
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail="A show with this slug already exists.",
            )

        show.slug = payload.slug

    if payload.title is not None:
        show.title = payload.title

    if payload.description is not None:
        show.description = payload.description

    if payload.section is not None:
        show.section = payload.section

    if payload.status is not None:
        show.status = payload.status

    if payload.categories is not None:
        show.categories.clear()

        for category in payload.categories:
            show.categories.append(
                ShowCategory(category=category)
            )

    db.commit()
    db.refresh(show)

    return serialize_show(show)


@app.delete("/admin/shows/{show_id}")
def delete_show(
    show_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_editor_or_admin),
):
    show = (
        db.query(Show)
        .filter(Show.id == show_id)
        .first()
    )

    if not show:
        raise HTTPException(
            status_code=404,
            detail="Show not found.",
        )

    db.delete(show)
    db.commit()

    return {
        "message": "Show deleted successfully.",
        "show_id": show_id,
    }


# =========================================================
# SEASON CRUD
# =========================================================

@app.get("/admin/seasons")
def get_seasons(
    show_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_editor_or_admin),
):
    query = db.query(Season)

    if show_id is not None:
        query = query.filter(
            Season.show_id == show_id
        )

    seasons = (
        query
        .order_by(
            Season.show_id,
            Season.season_number,
        )
        .all()
    )

    return [
        serialize_season(season)
        for season in seasons
    ]


@app.post("/admin/seasons")
def create_season(
    payload: SeasonCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_editor_or_admin),
):
    show = (
        db.query(Show)
        .filter(Show.id == payload.show_id)
        .first()
    )

    if not show:
        raise HTTPException(
            status_code=404,
            detail="Show not found.",
        )

    existing = (
        db.query(Season)
        .filter(
            Season.show_id == payload.show_id,
            Season.season_number == payload.season_number,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail="This season already exists for the show.",
        )

    season = Season(
        show_id=payload.show_id,
        season_number=payload.season_number,
        title=payload.title
        or f"Season {payload.season_number}",
    )

    db.add(season)
    db.commit()
    db.refresh(season)

    return serialize_season(season)


@app.put("/admin/seasons/{season_id}")
def update_season(
    season_id: int,
    payload: SeasonUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_editor_or_admin),
):
    season = (
        db.query(Season)
        .filter(Season.id == season_id)
        .first()
    )

    if not season:
        raise HTTPException(
            status_code=404,
            detail="Season not found.",
        )

    if payload.season_number is not None:

        existing = (
            db.query(Season)
            .filter(
                Season.show_id == season.show_id,
                Season.season_number
                == payload.season_number,
                Season.id != season_id,
            )
            .first()
        )

        if existing:
            raise HTTPException(
                status_code=409,
                detail="This season already exists.",
            )

        season.season_number = payload.season_number

    if payload.title is not None:
        season.title = payload.title

    db.commit()
    db.refresh(season)

    return serialize_season(season)


@app.delete("/admin/seasons/{season_id}")
def delete_season(
    season_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_editor_or_admin),
):
    season = (
        db.query(Season)
        .filter(Season.id == season_id)
        .first()
    )

    if not season:
        raise HTTPException(
            status_code=404,
            detail="Season not found.",
        )

    db.delete(season)
    db.commit()

    return {
        "message": "Season deleted successfully.",
        "season_id": season_id,
    }


# =========================================================
# EPISODE CRUD
# =========================================================

@app.get("/admin/episodes")
def get_episodes(
    show_id: int | None = Query(default=None),
    season_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    current_user=Depends(require_editor_or_admin),
):
    query = db.query(Episode)

    if season_id is not None:
        query = query.filter(
            Episode.season_id == season_id
        )

    elif show_id is not None:
        query = (
            query
            .join(Season)
            .filter(Season.show_id == show_id)
        )

    episodes = (
        query
        .order_by(
            Episode.season_id,
            Episode.episode_number,
            Episode.id,
        )
        .all()
    )

    return [
        serialize_episode(episode)
        for episode in episodes
    ]


@app.post("/admin/episodes")
def create_episode(
    payload: EpisodeCreate,
    db: Session = Depends(get_db),
    current_user=Depends(require_editor_or_admin),
):
    season = (
        db.query(Season)
        .filter(Season.id == payload.season_id)
        .first()
    )

    if not season:
        raise HTTPException(
            status_code=404,
            detail="Season not found.",
        )

    existing = (
        db.query(Episode)
        .filter(
            Episode.content_group
            == payload.content_group,
            Episode.language
            == payload.language,
        )
        .first()
    )

    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                "An episode with this "
                "content_group and language already exists."
            ),
        )

    episode = Episode(
        season_id=payload.season_id,
        episode_number=payload.episode_number,
        title=payload.title,
        description=payload.description,
        duration=payload.duration,
        language=payload.language,
        content_group=payload.content_group,
        status=payload.status,
    )

    db.add(episode)
    db.commit()
    db.refresh(episode)

    return serialize_episode(episode)


@app.put("/admin/episodes/{episode_id}")
def update_episode(
    episode_id: int,
    payload: EpisodeUpdate,
    db: Session = Depends(get_db),
    current_user=Depends(require_editor_or_admin),
):
    episode = (
        db.query(Episode)
        .filter(Episode.id == episode_id)
        .first()
    )

    if not episode:
        raise HTTPException(
            status_code=404,
            detail="Episode not found.",
        )

    new_content_group = (
        payload.content_group
        if payload.content_group is not None
        else episode.content_group
    )

    new_language = (
        payload.language
        if payload.language is not None
        else episode.language
    )

    duplicate = (
        db.query(Episode)
        .filter(
            Episode.content_group == new_content_group,
            Episode.language == new_language,
            Episode.id != episode_id,
        )
        .first()
    )

    if duplicate:
        raise HTTPException(
            status_code=409,
            detail=(
                "An episode with this "
                "content_group and language already exists."
            ),
        )

    if payload.season_id is not None:

        season = (
            db.query(Season)
            .filter(Season.id == payload.season_id)
            .first()
        )

        if not season:
            raise HTTPException(
                status_code=404,
                detail="Season not found.",
            )

        episode.season_id = payload.season_id

    if payload.episode_number is not None:
        episode.episode_number = payload.episode_number

    if payload.title is not None:
        episode.title = payload.title

    if payload.description is not None:
        episode.description = payload.description

    if payload.duration is not None:
        episode.duration = payload.duration

    if payload.language is not None:
        episode.language = payload.language

    if payload.content_group is not None:
        episode.content_group = payload.content_group

    if payload.status is not None:
        episode.status = payload.status

    db.commit()
    db.refresh(episode)

    return serialize_episode(episode)


@app.delete("/admin/episodes/{episode_id}")
def delete_episode(
    episode_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_editor_or_admin),
):
    episode = (
        db.query(Episode)
        .filter(Episode.id == episode_id)
        .first()
    )

    if not episode:
        raise HTTPException(
            status_code=404,
            detail="Episode not found.",
        )

    db.delete(episode)
    db.commit()

    return {
        "message": "Episode deleted successfully.",
        "episode_id": episode_id,
    }


# =========================================================
# ARTWORK
# =========================================================

@app.post("/admin/artwork/upload")
async def upload_artwork(
    artwork_type: str = Query(...),
    episode_id: int | None = Query(default=None),
    show_id: int | None = Query(default=None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user=Depends(require_editor_or_admin),
):
    if (episode_id is None) == (show_id is None):
        raise HTTPException(
            status_code=400,
            detail=(
                "Provide exactly one of episode_id "
                "or show_id."
            ),
        )

    episode = None

    if episode_id is not None:
        episode = (
            db.query(Episode)
            .filter(Episode.id == episode_id)
            .first()
        )

        if not episode:
            raise HTTPException(
                status_code=404,
                detail="Episode not found.",
            )

    show = None

    if show_id is not None:
        show = (
            db.query(Show)
            .filter(Show.id == show_id)
            .first()
        )

        if not show:
            raise HTTPException(
                status_code=404,
                detail="Show not found.",
            )

    existing_query = db.query(Artwork).filter(
        Artwork.artwork_type == artwork_type
    )

    if episode_id is not None:
        existing = (
            existing_query
            .filter(Artwork.episode_id == episode_id)
            .first()
        )
    else:
        existing = (
            existing_query
            .filter(Artwork.show_id == show_id)
            .first()
        )

    if existing:
        raise HTTPException(
            status_code=409,
            detail=(
                f"{artwork_type.title()} artwork "
                "already exists."
            ),
        )

    file_bytes = await file.read()

    valid, error_message = validate_artwork(
        file_bytes,
        artwork_type,
    )

    if not valid:
        raise HTTPException(
            status_code=400,
            detail=error_message,
        )

    original_suffix = Path(
        file.filename or ""
    ).suffix.lower()

    if original_suffix not in {
        ".jpg",
        ".jpeg",
        ".png",
        ".webp",
    }:
        original_suffix = ".jpg"

    if episode_id is not None:
        filename = (
            f"ep_{episode_id}"
            f"{original_suffix}"
        )
    else:
        filename = (
            f"show_{show_id}"
            f"{original_suffix}"
        )

    target_dir = ASSETS_DIR / artwork_type

    target_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    target_path = target_dir / filename

    if target_path.exists():
        raise HTTPException(
            status_code=409,
            detail="A file with this name already exists.",
        )

    target_path.write_bytes(file_bytes)

    from PIL import Image
    from io import BytesIO

    image = Image.open(
        BytesIO(file_bytes)
    )

    width, height = image.size

    artwork = Artwork(
        episode_id=episode_id,
        show_id=show_id,
        artwork_type=artwork_type,
        file_path=str(
            target_path.relative_to(BASE_DIR)
        ),
        width=width,
        height=height,
        file_size=len(file_bytes),
    )

    db.add(artwork)
    db.commit()
    db.refresh(artwork)

    return {
        "message": "Artwork uploaded successfully.",
        "episode_id": episode_id,
        "show_id": show_id,
        **serialize_artwork(artwork),
    }


# =========================================================
# VALIDATION REPORT
# =========================================================

@app.get("/admin/validation-report")
def get_validation_report(
    db: Session = Depends(get_db),
    current_user=Depends(require_editor_or_admin),
):
    issues = validate_database(db)

    blocking_issues = [
        issue
        for issue in issues
        if issue["type"] == "blocking"
    ]

    warnings = [
        issue
        for issue in issues
        if issue["type"] == "warning"
    ]

    return {
        "total_issues": len(issues),
        "blocking_issues": len(blocking_issues),
        "warnings": len(warnings),
        "issues": issues,
    }


# =========================================================
# RESOLVE VALIDATION ISSUE
# =========================================================

@app.patch("/admin/validation-issues/{issue_id}/resolve")
def resolve_validation_issue(
    issue_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(require_editor_or_admin),
):
    issue = (
        db.query(ValidationIssue)
        .filter(ValidationIssue.id == issue_id)
        .first()
    )

    if not issue:
        raise HTTPException(
            status_code=404,
            detail="Validation issue not found.",
        )

    if issue.resolved == "resolved":
        return {
            "message": "Validation issue is already resolved.",
            "issue_id": issue.id,
            "status": issue.resolved,
        }

    issue.resolved = "resolved"

    db.commit()
    db.refresh(issue)

    return {
        "message": "Validation issue resolved successfully.",
        "issue_id": issue.id,
        "seed_episode_id": issue.seed_episode_id,
        "status": issue.resolved,
    }


# =========================================================
# PUBLISH CATALOGUE
# =========================================================

@app.post("/admin/catalog/publish")
def publish_catalog(
    db: Session = Depends(get_db),
    current_user=Depends(require_admin),
):
    issues = validate_database(db)

    blocking_issues = [
        issue
        for issue in issues
        if issue["type"] == "blocking"
    ]

    if blocking_issues:

        publish_run = PublishRun(
            published_by=current_user["username"],
            shows_count=0,
            episodes_count=0,
            outcome="failed",
            error_message=(
                "Publish blocked by validation errors."
            ),
        )

        db.add(publish_run)
        db.commit()

        return {
            "message": "Publish blocked by validation errors.",
            "outcome": "failed",
            "blocking_issues": blocking_issues,
        }

    try:
        catalogue = build_catalogue(db)

        shows_count = len(
            catalogue.get("shows", [])
        )

        episodes_count = 0

        for show in catalogue.get("shows", []):

            for season in show.get("seasons", []):

                episodes_count += len(
                    season.get("episodes", [])
                )

        write_catalogue_atomically(
            catalogue
        )

        publish_run = PublishRun(
            published_by=current_user["username"],
            shows_count=shows_count,
            episodes_count=episodes_count,
            outcome="success",
            error_message=None,
        )

        db.add(publish_run)
        db.commit()
        db.refresh(publish_run)

        return {
            "message": "Catalogue published successfully.",
            "outcome": "success",
            "publish_run_id": publish_run.id,
            "shows_count": shows_count,
            "episodes_count": episodes_count,
            "published_by": current_user["username"],
        }

    except Exception as exc:

        db.rollback()

        publish_run = PublishRun(
            published_by=current_user["username"],
            shows_count=0,
            episodes_count=0,
            outcome="failed",
            error_message=str(exc),
        )

        db.add(publish_run)
        db.commit()

        return {
            "message": "Catalogue publish failed.",
            "outcome": "failed",
            "error": str(exc),
        }


# =========================================================
# PUBLISH HISTORY
# =========================================================

@app.get("/admin/catalog/publish-runs")
def get_publish_runs(
    db: Session = Depends(get_db),
    current_user=Depends(require_editor_or_admin),
):
    runs = (
        db.query(PublishRun)
        .order_by(
            PublishRun.id.desc()
        )
        .all()
    )

    return [
        {
            "id": run.id,
            "published_at": run.published_at,
            "published_by": run.published_by,
            "shows_count": run.shows_count,
            "episodes_count": run.episodes_count,
            "outcome": run.outcome,
            "error_message": run.error_message,
        }
        for run in runs
    ]


# =========================================================
# PUBLIC CATALOGUE
# =========================================================

@app.get("/catalog")
def get_catalog():
    return read_catalogue()


# =========================================================
# CATALOGUE SEARCH
# =========================================================

@app.get("/catalog/search")
def search_catalog(
    q: str | None = Query(default=None),
    category: str | None = Query(default=None),
    language: str | None = Query(default=None),
    section: str | None = Query(default=None),
):
    catalogue = read_catalogue()

    query_text = (
        q.strip().lower()
        if q
        else None
    )

    results = []

    for show in catalogue.get("shows", []):

        # Section filter.
        if (
            section
            and show.get("section") != section
        ):
            continue

        # Category filter.
        show_categories = [
            str(category_value).lower()
            for category_value
            in show.get("categories", [])
        ]

        if (
            category
            and category.lower()
            not in show_categories
        ):
            continue

        # Search show-level fields.
        show_matches_query = False

        if query_text:

            title = (
                show.get("title") or ""
            ).lower()

            description = (
                show.get("description") or ""
            ).lower()

            category_text = " ".join(
                show_categories
            )

            show_matches_query = (
                query_text in title
                or query_text in description
                or query_text in category_text
            )

        filtered_seasons = []

        for season in show.get(
            "seasons",
            [],
        ):

            filtered_episodes = []

            for episode in season.get(
                "episodes",
                [],
            ):

                # Language filter.
                languages = [
                    str(lang).lower()
                    for lang
                    in episode.get(
                        "languages",
                        [],
                    )
                ]

                if (
                    language
                    and language.lower()
                    not in languages
                ):
                    continue

                # Episode query matching.
                episode_matches_query = False

                if query_text:

                    episode_title = (
                        episode.get("title")
                        or ""
                    ).lower()

                    episode_matches_query = (
                        query_text
                        in episode_title
                    )

                if (
                    query_text
                    and not show_matches_query
                    and not episode_matches_query
                ):
                    continue

                filtered_episodes.append(
                    episode
                )

            if filtered_episodes:
                filtered_seasons.append({
                    **season,
                    "episodes": filtered_episodes,
                })

        # If query matched the show itself,
        # include all episodes that passed filters.
        if query_text and show_matches_query:

            filtered_seasons = []

            for season in show.get(
                "seasons",
                [],
            ):

                filtered_episodes = []

                for episode in season.get(
                    "episodes",
                    [],
                ):

                    languages = [
                        str(lang).lower()
                        for lang
                        in episode.get(
                            "languages",
                            [],
                        )
                    ]

                    if (
                        language
                        and language.lower()
                        not in languages
                    ):
                        continue

                    filtered_episodes.append(
                        episode
                    )

                if filtered_episodes:
                    filtered_seasons.append({
                        **season,
                        "episodes": filtered_episodes,
                    })

        # No search query means normal filtering.
        if not query_text:

            if filtered_seasons:
                results.append({
                    **show,
                    "seasons": filtered_seasons,
                })

        elif filtered_seasons:

            results.append({
                **show,
                "seasons": filtered_seasons,
            })

    return {
        "count": len(results),
        "shows": results,
    }