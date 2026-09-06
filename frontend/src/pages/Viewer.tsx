import { useEffect, useMemo, useState } from "react";
import { getCatalogue, searchCatalogue } from "../services/api";
import type {
  CatalogueResponse,
  CatalogueShow,
  SearchResponse,
} from "../types/catalogue";

const API_BASE_URL = "http://127.0.0.1:8000";

type ArtworkMap = {
  poster?: string;
  banner?: string;
  thumbnail?: string;
};

type EpisodeData = {
  episode_id?: string;
  title: string;
  episode_number: number;
  duration_seconds: number;
  languages: string[];
  artwork?: ArtworkMap;
  variants?: Array<{
    language: string;
    title: string;
    duration_seconds: number;
    artwork?: ArtworkMap;
  }>;
};

type SeasonData = {
  season_number: number;
  title?: string;
  episodes: EpisodeData[];
};

type ShowData = CatalogueShow & {
  artwork?: ArtworkMap;
  seasons: SeasonData[];
};

function imageUrl(path?: string) {
  if (!path) {
    return "";
  }

  if (path.startsWith("http")) {
    return path;
  }

  return `${API_BASE_URL}${path}`;
}

function getShowArtwork(
  show: ShowData,
  type: "banner" | "poster" | "thumbnail",
) {
  return show.artwork?.[type];
}

function getEpisodeArtwork(
  episode: EpisodeData,
  type: "poster" | "thumbnail" | "banner",
) {
  return episode.artwork?.[type];
}

function formatDuration(seconds: number) {
  if (!seconds || seconds <= 0) {
    return "";
  }

  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  if (remainingSeconds === 0) {
    return `${minutes} min`;
  }

  return `${minutes}m ${remainingSeconds}s`;
}

export default function Viewer() {
  const [catalogue, setCatalogue] =
    useState<CatalogueResponse | null>(null);

  const [shows, setShows] = useState<ShowData[]>([]);

  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("");
  const [language, setLanguage] = useState("");

  const [loading, setLoading] = useState(true);
  const [searching, setSearching] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    async function loadCatalogue() {
      try {
        setLoading(true);
        setError("");

        const data = await getCatalogue<CatalogueResponse>();

        setCatalogue(data);
        setShows((data.shows ?? []) as ShowData[]);
      } catch (err) {
        setError(
          err instanceof Error
            ? err.message
            : "Unable to load the catalogue.",
        );
      } finally {
        setLoading(false);
      }
    }

    loadCatalogue();
  }, []);

  const categories = useMemo(() => {
    const values = new Set<string>();

    const sourceShows = (catalogue?.shows ?? []) as ShowData[];

    sourceShows.forEach((show) => {
      (show.categories ?? []).forEach((item) => {
        values.add(item);
      });
    });

    return Array.from(values).sort();
  }, [catalogue]);

  const languages = useMemo(() => {
    const values = new Set<string>();

    const sourceShows = (catalogue?.shows ?? []) as ShowData[];

    sourceShows.forEach((show) => {
      (show.seasons ?? []).forEach((season) => {
        (season.episodes ?? []).forEach((episode) => {
          (episode.languages ?? []).forEach((item) => {
            values.add(item);
          });
        });
      });
    });

    return Array.from(values).sort();
  }, [catalogue]);

  async function handleSearch() {
    try {
      setSearching(true);
      setError("");

      if (!query.trim() && !category && !language) {
        setShows((catalogue?.shows ?? []) as ShowData[]);
        return;
      }

      const data = await searchCatalogue<SearchResponse>(
        query.trim(),
        category,
        language,
      );

      setShows((data.results ?? []) as ShowData[]);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to search the catalogue.",
      );
    } finally {
      setSearching(false);
    }
  }

  function clearFilters() {
    setQuery("");
    setCategory("");
    setLanguage("");
    setShows((catalogue?.shows ?? []) as ShowData[]);
    setError("");
  }

  if (loading) {
    return (
      <div className="page-message">
        <h2>Loading Peblo TV...</h2>
        <p>Please wait while the catalogue is loading.</p>
      </div>
    );
  }

  if (error && !catalogue) {
    return (
      <div className="page-message error">
        <h2>Unable to load Peblo TV</h2>
        <p>{error}</p>
      </div>
    );
  }

  const heroShow = shows.length > 0 ? shows[0] : undefined;

  const heroBanner = heroShow
    ? getShowArtwork(heroShow, "banner")
    : undefined;

  return (
    <main className="viewer">
      {/* HEADER */}
      <header className="viewer-header">
        <div>
          <p className="brand">PEBLO TV</p>
          <p className="subtitle">
            Entertainment for curious minds
          </p>
        </div>

        <nav>
          <a href="/cms">CMS</a>
        </nav>
      </header>

      {/* HERO */}
      <section
        className="hero"
        style={
          heroBanner
            ? {
                backgroundImage: `
                  linear-gradient(
                    90deg,
                    rgba(8, 8, 12, 0.96) 0%,
                    rgba(8, 8, 12, 0.72) 45%,
                    rgba(8, 8, 12, 0.25) 100%
                  ),
                  url("${imageUrl(heroBanner)}")
                `,
              }
            : undefined
        }
      >
        <div className="hero-content">
          <span className="hero-label">FEATURED</span>

          <h1>
            {heroShow?.title ?? "Peblo TV"}
          </h1>

          <p>
            {heroShow?.description ??
              "Discover shows, stories and educational adventures."}
          </p>

          {heroShow && (
            <div className="hero-tags">
              {(heroShow.categories ?? []).map((item) => (
                <span key={item}>
                  {item}
                </span>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* SEARCH */}
      <section className="catalogue-controls">
        <input
          type="search"
          placeholder="Search shows, episodes or categories..."
          value={query}
          onChange={(event) =>
            setQuery(event.target.value)
          }
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              handleSearch();
            }
          }}
        />

        <select
          value={category}
          onChange={(event) =>
            setCategory(event.target.value)
          }
        >
          <option value="">All categories</option>

          {categories.map((item) => (
            <option key={item} value={item}>
              {item}
            </option>
          ))}
        </select>

        <select
          value={language}
          onChange={(event) =>
            setLanguage(event.target.value)
          }
        >
          <option value="">All languages</option>

          {languages.map((item) => (
            <option key={item} value={item}>
              {item.toUpperCase()}
            </option>
          ))}
        </select>

        <button
          onClick={handleSearch}
          disabled={searching}
        >
          {searching ? "Searching..." : "Search"}
        </button>

        <button
          className="secondary-button"
          onClick={clearFilters}
        >
          Clear
        </button>
      </section>

      {/* ERROR */}
      {error && (
        <div className="inline-error">
          {error}
        </div>
      )}

      {/* EMPTY STATE */}
      {shows.length === 0 ? (
        <div className="page-message">
          <h2>No shows found</h2>
          <p>
            Try changing your search or filters.
          </p>
        </div>
      ) : (
        <section className="show-sections">
          {shows.map((show) => (
            <article
              className="show-row"
              key={show.show_id}
            >
              {/* SHOW HEADER */}
              <div className="show-heading">
                <div>
                  <h2>{show.title}</h2>

                  <p>
                    {show.description}
                  </p>
                </div>

                {show.section && (
                  <span className="section-badge">
                    {show.section}
                  </span>
                )}
              </div>

              {/* SEASONS */}
              {(show.seasons ?? [])
                .filter(
                  (season) =>
                    season.season_number !== 0,
                )
                .map((season) => (
                  <div
                    className="season-section"
                    key={`${show.show_id}-${season.season_number}`}
                  >
                    <h3 className="season-title">
                      {season.title ??
                        `Season ${season.season_number}`}
                    </h3>

                    {/* EPISODES */}
                    <div className="poster-row">
                      {(season.episodes ?? []).map(
                        (episode) => {
                          const poster =
                            getEpisodeArtwork(
                              episode,
                              "poster",
                            );

                          const thumbnail =
                            getEpisodeArtwork(
                              episode,
                              "thumbnail",
                            );

                          const artwork =
                            poster ?? thumbnail;

                          return (
                            <div
                              className="episode-card"
                              key={
                                episode.episode_id ??
                                `${show.show_id}-${season.season_number}-${episode.episode_number}`
                              }
                            >
                              {/* IMAGE */}
                              <div className="poster-wrapper">
                                {artwork ? (
                                  <img
                                    src={imageUrl(
                                      artwork,
                                    )}
                                    alt={
                                      episode.title
                                    }
                                    loading="lazy"
                                  />
                                ) : (
                                  <div className="poster-placeholder">
                                    <span>
                                      No artwork
                                    </span>
                                  </div>
                                )}
                              </div>

                              {/* TITLE */}
                              <h3>
                                {episode.title}
                              </h3>

                              {/* EPISODE NUMBER */}
                              <p>
                                S
                                {String(
                                  season.season_number,
                                ).padStart(2, "0")}{" "}
                                · E
                                {String(
                                  episode.episode_number,
                                ).padStart(2, "0")}
                              </p>

                              {/* DURATION */}
                              {episode.duration_seconds >
                                0 && (
                                <small className="duration">
                                  {formatDuration(
                                    episode.duration_seconds,
                                  )}
                                </small>
                              )}

                              {/* LANGUAGES */}
                              <div className="language-list">
                                {(
                                  episode.languages ??
                                  []
                                ).map((item) => (
                                  <span
                                    key={item}
                                  >
                                    {item.toUpperCase()}
                                  </span>
                                ))}
                              </div>

                              {/* LANGUAGE VARIANTS */}
                              {episode.variants &&
                                episode.variants.length >
                                  1 && (
                                  <div className="variant-info">
                                    {
                                      episode
                                        .variants
                                        .length
                                    }{" "}
                                    language versions
                                  </div>
                                )}
                            </div>
                          );
                        },
                      )}
                    </div>
                  </div>
                ))}
            </article>
          ))}
        </section>
      )}

      {/* FOOTER */}
      <footer className="viewer-footer">
        Catalogue version{" "}
        {catalogue?.version ?? 1}
      </footer>
    </main>
  );
}