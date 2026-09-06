from sqlalchemy import func
from sqlalchemy.orm import Session

from models import Show, Season, Episode, Artwork, ValidationIssue


VALID_SECTIONS = {
    "featured",
    "series",
    "minisodes",
    "songs",
}

VALID_LANGUAGES = {
    "en",
    "hi",
}


def validate_database(db: Session):
    issues = []

    shows = db.query(Show).all()

    for show in shows:

        # Published shows must have a section.
        if show.status == "published" and not show.section:
            issues.append({
                "type": "blocking",
                "entity": "show",
                "entity_id": show.id,
                "show": show.title,
                "message": "Published show must have a section.",
            })

        # Section must be one of the allowed values.
        if show.section and show.section not in VALID_SECTIONS:
            issues.append({
                "type": "blocking",
                "entity": "show",
                "entity_id": show.id,
                "show": show.title,
                "message": f"Invalid section: {show.section}",
            })

        # Draft shows without a section are warnings.
        if show.status == "draft" and not show.section:
            issues.append({
                "type": "warning",
                "entity": "show",
                "entity_id": show.id,
                "show": show.title,
                "message": "Draft show does not have a section yet.",
            })

        for season in show.seasons:

            for episode in season.episodes:

                # Published episodes need a valid duration.
                if episode.status == "published":

                    if not episode.duration or episode.duration <= 0:
                        issues.append({
                            "type": "blocking",
                            "entity": "episode",
                            "entity_id": (
                                episode.seed_episode_id
                                or episode.id
                            ),
                            "show": show.title,
                            "message": (
                                "Published episode must have "
                                "a valid duration."
                            ),
                        })

                    # Published episodes need artwork.
                    if not episode.artwork:
                        issues.append({
                            "type": "blocking",
                            "entity": "episode",
                            "entity_id": (
                                episode.seed_episode_id
                                or episode.id
                            ),
                            "show": show.title,
                            "message": (
                                "Published episode must have artwork."
                            ),
                        })

                # Language validation.
                if episode.language not in VALID_LANGUAGES:
                    issues.append({
                        "type": "blocking",
                        "entity": "episode",
                        "entity_id": (
                            episode.seed_episode_id
                            or episode.id
                        ),
                        "show": show.title,
                        "message": (
                            f"Invalid language: "
                            f"{episode.language}"
                        ),
                    })

    # ---------------------------------------------------------
    # Detect duplicate content_group + language
    # ---------------------------------------------------------

    duplicate_groups = (
        db.query(
            Episode.content_group,
            Episode.language,
        )
        .group_by(
            Episode.content_group,
            Episode.language,
        )
        .having(func.count(Episode.id) > 1)
        .all()
    )

    for content_group, language in duplicate_groups:

        duplicate_episodes = (
            db.query(Episode)
            .filter(
                Episode.content_group == content_group,
                Episode.language == language,
            )
            .all()
        )

        for episode in duplicate_episodes:

            show_title = None

            if episode.season and episode.season.show:
                show_title = episode.season.show.title

            issues.append({
                "type": "blocking",
                "entity": "episode",
                "entity_id": (
                    episode.seed_episode_id
                    or episode.id
                ),
                "show": show_title,
                "message": (
                    "Duplicate content_group + language: "
                    f"{content_group} + {language}"
                ),
            })

    # ---------------------------------------------------------
    # Include saved validation issues
    # ---------------------------------------------------------

    saved_issues = (
        db.query(ValidationIssue)
        .filter(
            ValidationIssue.resolved == "open"
        )
        .all()
    )

    for saved_issue in saved_issues:

        show_title = None

        # First try to find the episode directly.
        if saved_issue.seed_episode_id:

            saved_episode = (
                db.query(Episode)
                .filter(
                    Episode.seed_episode_id
                    == saved_issue.seed_episode_id
                )
                .first()
            )

            if saved_episode:
                if (
                    saved_episode.season
                    and saved_episode.season.show
                ):
                    show_title = (
                        saved_episode.season.show.title
                    )

        # -----------------------------------------------------
        # The duplicate ep_9001 was skipped during import.
        # Therefore it does not exist as an Episode row.
        #
        # Extract its content_group from the saved message
        # and find the existing episode with the same group.
        # -----------------------------------------------------

        if show_title is None:
            message = saved_issue.message or ""

            prefix = "Duplicate content_group + language: "

            if message.startswith(prefix):

                duplicate_details = message[len(prefix):]

                content_group = duplicate_details.split(
                    " + ",
                    1,
                )[0].strip()

                reference_episode = (
                    db.query(Episode)
                    .filter(
                        Episode.content_group
                        == content_group
                    )
                    .first()
                )

                if reference_episode:
                    if (
                        reference_episode.season
                        and reference_episode.season.show
                    ):
                        show_title = (
                            reference_episode
                            .season
                            .show
                            .title
                        )

        issues.append({
            "type": saved_issue.issue_type,
            "entity": saved_issue.entity,
            "entity_id": saved_issue.seed_episode_id,
            "show": show_title,
            "message": saved_issue.message,
        })

    return issues