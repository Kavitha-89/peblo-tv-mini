import { useEffect, useState } from "react";
import { apiRequest, getAuthHeaders } from "../services/api";
import ArtworkUpload from "./ArtworkUpload";

type UserRole = "admin" | "editor";

type CurrentUser = {
  username: string;
  role: UserRole;
};

type Show = {
  show_id: number;
  slug: string;
  title: string;
  description?: string;
  section?: string | null;
  categories?: string[];
  status?: string;
};

type ValidationIssue = {
  type: "blocking" | "warning" | string;
  entity: string;
  entity_id?: number;
  show?: string;
  message: string;
};

type ValidationReport = {
  total_issues: number;
  blocking_issues: number;
  warnings: number;
  issues: ValidationIssue[];
};

type PublishResponse = {
  message: string;
  outcome: string;
  publish_run_id: number;
  shows_count: number;
  episodes_count: number;
  published_by: string;
};

type ShowForm = {
  slug: string;
  title: string;
  description: string;
  section: string;
  categories: string;
  status: string;
};

const emptyForm: ShowForm = {
  slug: "",
  title: "",
  description: "",
  section: "",
  categories: "",
  status: "draft",
};

export default function CMS() {
  const [user, setUser] = useState<CurrentUser | null>(null);

  const [shows, setShows] = useState<Show[]>([]);
  const [validation, setValidation] =
    useState<ValidationReport | null>(null);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [publishing, setPublishing] = useState(false);

  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [search, setSearch] = useState("");

  const [showForm, setShowForm] =
    useState<ShowForm>(emptyForm);

  const [editingShowId, setEditingShowId] =
    useState<number | null>(null);

  const [savingShow, setSavingShow] = useState(false);

  useEffect(() => {
    const savedUser = localStorage.getItem("peblo_user");

    if (!savedUser) {
      setLoading(false);
      return;
    }

    try {
      const parsed = JSON.parse(savedUser) as CurrentUser;

      if (
        parsed.username &&
        (parsed.role === "admin" || parsed.role === "editor")
      ) {
        setUser(parsed);
      }
    } catch {
      localStorage.removeItem("peblo_user");
      localStorage.removeItem("peblo_access_token");
    }

    setLoading(false);
  }, []);

  useEffect(() => {
    if (user) {
      loadDashboard();
    }
  }, [user]);

  async function loadDashboard() {
    try {
      setRefreshing(true);
      setError("");

      const headers = getAuthHeaders();

      const [showsData, validationData] = await Promise.all([
        apiRequest<Show[]>("/admin/shows", {
          headers,
        }),
        apiRequest<ValidationReport>(
          "/admin/validation-report",
          {
            headers,
          },
        ),
      ]);

      setShows(showsData ?? []);
      setValidation(validationData);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to load the CMS dashboard.",
      );
    } finally {
      setRefreshing(false);
    }
  }

  async function handlePublish() {
    if (!user || user.role !== "admin") {
      return;
    }

    const confirmed = window.confirm(
      "Publish the current catalogue?\n\nOnly validated published content will appear in the public catalogue.",
    );

    if (!confirmed) {
      return;
    }

    try {
      setPublishing(true);
      setError("");
      setSuccess("");

      const result = await apiRequest<PublishResponse>(
        "/admin/catalog/publish",
        {
          method: "POST",
          headers: getAuthHeaders(),
        },
      );

      setSuccess(
        `Catalogue published successfully. Run #${result.publish_run_id} published ${result.shows_count} shows and ${result.episodes_count} episodes.`,
      );

      await loadDashboard();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Catalogue publishing failed.",
      );
    } finally {
      setPublishing(false);
    }
  }

  async function handleSaveShow(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    if (!user) {
      return;
    }

    if (!showForm.slug.trim() || !showForm.title.trim()) {
      setError("Show title and slug are required.");
      return;
    }

    try {
      setSavingShow(true);
      setError("");
      setSuccess("");

      const payload = {
        slug: showForm.slug.trim(),
        title: showForm.title.trim(),
        description:
          showForm.description.trim() || null,
        section:
          showForm.section.trim() || null,
        status: showForm.status,
        categories: showForm.categories
          .split(",")
          .map((item) => item.trim())
          .filter(Boolean),
      };

      if (editingShowId !== null) {
        await apiRequest(
          `/admin/shows/${editingShowId}`,
          {
            method: "PUT",
            headers: getAuthHeaders(),
            body: JSON.stringify(payload),
          },
        );

        setSuccess("Show updated successfully.");
      } else {
        await apiRequest(
          "/admin/shows",
          {
            method: "POST",
            headers: getAuthHeaders(),
            body: JSON.stringify(payload),
          },
        );

        setSuccess("Show created successfully.");
      }

      setShowForm(emptyForm);
      setEditingShowId(null);

      await loadDashboard();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to save the show.",
      );
    } finally {
      setSavingShow(false);
    }
  }

  function startEditing(show: Show) {
    setEditingShowId(show.show_id);

    setShowForm({
      slug: show.slug,
      title: show.title,
      description: show.description || "",
      section: show.section || "",
      categories: show.categories?.join(", ") || "",
      status: show.status || "draft",
    });

    setError("");
    setSuccess("");
  }

  function cancelEditing() {
    setEditingShowId(null);
    setShowForm(emptyForm);
    setError("");
  }

  async function handleDeleteShow(show: Show) {
    if (!user) {
      return;
    }

    const confirmed = window.confirm(
      `Delete "${show.title}"?\n\nThis may also remove its related seasons and episodes.`,
    );

    if (!confirmed) {
      return;
    }

    try {
      setError("");
      setSuccess("");

      await apiRequest(
        `/admin/shows/${show.show_id}`,
        {
          method: "DELETE",
          headers: getAuthHeaders(),
        },
      );

      setSuccess(`"${show.title}" deleted successfully.`);

      if (editingShowId === show.show_id) {
        cancelEditing();
      }

      await loadDashboard();
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Unable to delete the show.",
      );
    }
  }

  function handleLogout() {
    localStorage.removeItem("peblo_access_token");
    localStorage.removeItem("peblo_user");

    setUser(null);
    setShows([]);
    setValidation(null);
    setSuccess("");
    setError("");
  }

  if (loading) {
    return (
      <main className="cms-page">
        <div className="cms-card">
          <h2>Loading CMS...</h2>
          <p>Please wait.</p>
        </div>
      </main>
    );
  }

  if (!user) {
    return (
      <CMSLogin
        onLogin={(loggedInUser) => {
          setUser(loggedInUser);
        }}
      />
    );
  }

  const publishedShows = shows.filter(
    (show) => show.status === "published",
  );

  const draftShows = shows.filter(
    (show) => show.status !== "published",
  );

  const filteredShows = shows.filter((show) => {
    const text = [
      show.title,
      show.slug,
      show.section || "",
      ...(show.categories || []),
    ]
      .join(" ")
      .toLowerCase();

    return text.includes(search.toLowerCase());
  });

  return (
    <main className="cms-page">
      <header className="cms-header">
        <div>
          <p className="brand">PEBLO TV</p>

          <h1>Content Management System</h1>

          <p>
            Signed in as{" "}
            <strong>
              {user.username} ({user.role})
            </strong>
          </p>
        </div>

        <div className="cms-header-actions">
          <a href="/">Viewer</a>

          <button
            className="secondary-button"
            onClick={handleLogout}
          >
            Logout
          </button>
        </div>
      </header>

      {error && (
        <div className="cms-alert cms-alert-error">
          <strong>Error:</strong> {error}
        </div>
      )}

      {success && (
        <div className="cms-alert cms-alert-success">
          {success}
        </div>
      )}

      <section className="cms-stats">
        <div className="cms-stat-card">
          <span>Total Shows</span>
          <strong>{shows.length}</strong>
        </div>

        <div className="cms-stat-card">
          <span>Published Shows</span>
          <strong>{publishedShows.length}</strong>
        </div>

        <div className="cms-stat-card">
          <span>Draft Shows</span>
          <strong>{draftShows.length}</strong>
        </div>

        <div className="cms-stat-card">
          <span>Blocking Issues</span>

          <strong
            className={
              validation?.blocking_issues
                ? "stat-danger"
                : "stat-good"
            }
          >
            {validation?.blocking_issues ?? 0}
          </strong>
        </div>
      </section>

      <section className="cms-panel">
        <div className="cms-panel-header">
          <div>
            <h2>
              {editingShowId !== null
                ? "Edit Show"
                : "Create Show"}
            </h2>

            <p>
              {editingShowId !== null
                ? "Update the selected show's information."
                : "Add a new show to the CMS."}
            </p>
          </div>
        </div>

        <form
          className="show-form"
          onSubmit={handleSaveShow}
        >
          <div className="form-grid">
            <div>
              <label htmlFor="show-title">
                Show Title *
              </label>

              <input
                id="show-title"
                value={showForm.title}
                onChange={(event) =>
                  setShowForm({
                    ...showForm,
                    title: event.target.value,
                  })
                }
                placeholder="Example: Moti's Many Lives"
                required
              />
            </div>

            <div>
              <label htmlFor="show-slug">
                Slug *
              </label>

              <input
                id="show-slug"
                value={showForm.slug}
                onChange={(event) =>
                  setShowForm({
                    ...showForm,
                    slug: event.target.value,
                  })
                }
                placeholder="moti-many-lives"
                required
              />
            </div>

            <div>
              <label htmlFor="show-section">
                Section
              </label>

              <input
                id="show-section"
                value={showForm.section}
                onChange={(event) =>
                  setShowForm({
                    ...showForm,
                    section: event.target.value,
                  })
                }
                placeholder="Kids"
              />
            </div>

            <div>
              <label htmlFor="show-category">
                Categories
              </label>

              <input
                id="show-category"
                value={showForm.categories}
                onChange={(event) =>
                  setShowForm({
                    ...showForm,
                    categories: event.target.value,
                  })
                }
                placeholder="Adventure, India"
              />
            </div>

            <div>
              <label htmlFor="show-status">
                Status
              </label>

              <select
                id="show-status"
                value={showForm.status}
                onChange={(event) =>
                  setShowForm({
                    ...showForm,
                    status: event.target.value,
                  })
                }
              >
                <option value="draft">Draft</option>
                <option value="published">
                  Published
                </option>
              </select>
            </div>

            <div className="form-full">
              <label htmlFor="show-description">
                Description
              </label>

              <textarea
                id="show-description"
                value={showForm.description}
                onChange={(event) =>
                  setShowForm({
                    ...showForm,
                    description: event.target.value,
                  })
                }
                placeholder="Short description of the show"
                rows={4}
              />
            </div>
          </div>

          <div className="form-actions">
            <button
              type="submit"
              disabled={savingShow}
            >
              {savingShow
                ? "Saving..."
                : editingShowId !== null
                  ? "Update Show"
                  : "Create Show"}
            </button>

            {editingShowId !== null && (
              <button
                type="button"
                className="secondary-button"
                onClick={cancelEditing}
              >
                Cancel
              </button>
            )}
          </div>
        </form>
      </section>

      <section className="cms-panel">
        <div className="cms-panel-header">
          <div>
            <h2>Manage Shows</h2>

            <p>
              Search, edit and delete shows from the CMS.
            </p>
          </div>

          <button
            className="secondary-button"
            onClick={loadDashboard}
            disabled={refreshing}
          >
            {refreshing
              ? "Refreshing..."
              : "Refresh"}
          </button>
        </div>

        <div className="cms-search">
          <input
            value={search}
            onChange={(event) =>
              setSearch(event.target.value)
            }
            placeholder="Search shows, sections or categories..."
          />
        </div>

        {filteredShows.length === 0 ? (
          <div className="cms-empty">
            <h3>No shows found</h3>

            <p>
              Try a different search term.
            </p>
          </div>
        ) : (
          <div className="shows-table-wrapper">
            <table className="shows-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Show</th>
                  <th>Section</th>
                  <th>Categories</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>

              <tbody>
                {filteredShows.map((show) => (
                  <tr key={show.show_id}>
                    <td>{show.show_id}</td>

                    <td>
                      <strong>{show.title}</strong>
                      <small>{show.slug}</small>
                    </td>

                    <td>
                      {show.section || (
                        <span className="missing-value">
                          Not assigned
                        </span>
                      )}
                    </td>

                    <td>
                      {show.categories?.length
                        ? show.categories.join(", ")
                        : "—"}
                    </td>

                    <td>
                      <span
                        className={
                          show.status === "published"
                            ? "status-badge status-published"
                            : "status-badge status-draft"
                        }
                      >
                        {show.status || "draft"}
                      </span>
                    </td>

                    <td>
                      <div className="table-actions">
                        <button
                          className="small-button"
                          onClick={() =>
                            startEditing(show)
                          }
                        >
                          Edit
                        </button>

                        <button
                          className="small-button danger-button"
                          onClick={() =>
                            handleDeleteShow(show)
                          }
                        >
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section className="cms-dashboard-grid">
        <div className="cms-panel validation-panel">
          <div className="cms-panel-header">
            <div>
              <h2>Validation Report</h2>

              <p>
                Issues that editors should resolve before
                publishing.
              </p>
            </div>
          </div>

          {!validation ? (
            <div className="cms-empty">
              <p>
                Validation report unavailable.
              </p>
            </div>
          ) : (
            <>
              <div className="validation-summary">
                <div>
                  <strong>
                    {validation.total_issues}
                  </strong>
                  <span>Total issues</span>
                </div>

                <div>
                  <strong className="stat-danger">
                    {validation.blocking_issues}
                  </strong>
                  <span>Blocking</span>
                </div>

                <div>
                  <strong>
                    {validation.warnings}
                  </strong>
                  <span>Warnings</span>
                </div>
              </div>

              {validation.issues.length === 0 ? (
                <div className="validation-good">
                  ✓ No validation issues found.
                </div>
              ) : (
                <div className="validation-list">
                  {validation.issues.map(
                    (issue, index) => (
                      <div
                        className={
                          issue.type === "blocking"
                            ? "validation-item validation-blocking"
                            : "validation-item validation-warning"
                        }
                        key={`${issue.entity}-${issue.entity_id}-${index}`}
                      >
                        <div className="validation-item-title">
                          <strong>
                            {issue.type === "blocking"
                              ? "BLOCKING"
                              : "WARNING"}
                          </strong>

                          <span>
                            {issue.entity}
                            {issue.entity_id
                              ? ` #${issue.entity_id}`
                              : ""}
                          </span>
                        </div>

                        <p>{issue.message}</p>

                        {issue.show && (
                          <small>
                            Show: {issue.show}
                          </small>
                        )}
                      </div>
                    ),
                  )}
                </div>
              )}
            </>
          )}
        </div>
      </section>

      <section className="cms-panel">
      <ArtworkUpload episodeId={36}/>
      </section>

      <section className="cms-panel publish-panel">
        <div>
          <h2>Catalogue Publishing</h2>

          <p>
            Publishing creates a new catalogue snapshot from
            valid published content.
          </p>

          {validation?.blocking_issues ? (
            <p className="publish-warning">
              Publishing is blocked because there are{" "}
              <strong>
                {validation.blocking_issues}
              </strong>{" "}
              blocking validation issues.
            </p>
          ) : (
            <p className="publish-ready">
              ✓ No blocking validation issues detected.
            </p>
          )}
        </div>

        {user.role === "admin" ? (
          <button
            className="publish-button"
            onClick={handlePublish}
            disabled={
              publishing ||
              !!validation?.blocking_issues
            }
          >
            {publishing
              ? "Publishing..."
              : "Publish Catalogue"}
          </button>
        ) : (
          <div className="permission-note">
            Publishing is available to administrators only.
          </div>
        )}
      </section>

      <footer className="viewer-footer">
        Peblo TV CMS · {user.username} · {user.role}
      </footer>
    </main>
  );
}

type CMSLoginProps = {
  onLogin: (user: CurrentUser) => void;
};

function CMSLogin({ onLogin }: CMSLoginProps) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleLogin(
    event: React.FormEvent<HTMLFormElement>,
  ) {
    event.preventDefault();

    try {
      setLoading(true);
      setError("");

      const data = await apiRequest<{
        access_token: string;
        token_type: string;
        username: string;
        role: UserRole;
      }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({
          username,
          password,
        }),
      });

      const loggedInUser: CurrentUser = {
        username: data.username,
        role: data.role,
      };

      localStorage.setItem(
        "peblo_access_token",
        data.access_token,
      );

      localStorage.setItem(
        "peblo_user",
        JSON.stringify(loggedInUser),
      );

      onLogin(loggedInUser);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Invalid username or password.",
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="cms-page">
      <section className="login-card">
        <div className="login-heading">
          <p className="brand">PEBLO TV</p>

          <h1>CMS Login</h1>

          <p>
            Sign in to manage shows, episodes and catalogue
            publishing.
          </p>
        </div>

        <form onSubmit={handleLogin}>
          <label htmlFor="cms-username">
            Username
          </label>

          <input
            id="cms-username"
            type="text"
            value={username}
            onChange={(event) =>
              setUsername(event.target.value)
            }
            placeholder="Enter username"
            autoComplete="username"
            required
          />

          <label htmlFor="cms-password">
            Password
          </label>

          <input
            id="cms-password"
            type="password"
            value={password}
            onChange={(event) =>
              setPassword(event.target.value)
            }
            placeholder="Enter password"
            autoComplete="current-password"
            required
          />

          {error && (
            <div className="inline-error">
              {error}
            </div>
          )}

          <button type="submit" disabled={loading}>
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <div className="demo-credentials">
          <h3>Demo accounts</h3>

          <p>
            <strong>Admin:</strong> admin / admin123
          </p>

          <p>
            <strong>Editor:</strong> editor / editor123
          </p>
        </div>

        <a href="/" className="back-link">
          ← Back to Viewer
        </a>
      </section>
    </main>
  );
}