import { useState } from "react";
import { getAuthHeaders } from "../services/api";

type ArtworkType = "poster" | "banner" | "thumbnail";

type ArtworkUploadProps = {
  episodeId?: number;
  showId?: number;
};

const artworkRules = {
  poster: {
    label: "Poster",
    dimensions: "600 × 900 px",
  },
  banner: {
    label: "Banner",
    dimensions: "1280 × 720 px",
  },
  thumbnail: {
    label: "Thumbnail",
    dimensions: "640 × 360 px",
  },
};

export default function ArtworkUpload({
  episodeId,
  showId,
}: ArtworkUploadProps) {
  const [type, setType] =
    useState<ArtworkType>("poster");

  const [file, setFile] = useState<File | null>(null);

  const [uploading, setUploading] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  async function handleUpload() {
    if (!file) {
      setError("Please select an artwork file.");
      return;
    }

    if (!episodeId && !showId) {
      setError(
        "Select a show or episode before uploading artwork.",
      );
      return;
    }

    if (file.size > 200 * 1024) {
      setError(
        "Artwork must be smaller than 200 KB.",
      );
      return;
    }

    try {
      setUploading(true);
      setError("");
      setMessage("");

      const formData = new FormData();

      formData.append("file", file);

      const params = new URLSearchParams();

      params.set("artwork_type", type);

      if (episodeId) {
        params.set("episode_id", String(episodeId));
      }

      if (showId) {
        params.set("show_id", String(showId));
      }

      const response = await fetch(
        `http://127.0.0.1:8000/admin/artwork/upload?${params.toString()}`,
        {
          method: "POST",
          headers: getAuthHeaders(),
          body: formData,
        },
      );

      if (!response.ok) {
        let errorMessage =
          "Artwork upload failed.";

        try {
          const data = await response.json();

          if (typeof data.detail === "string") {
            errorMessage = data.detail;
          }
        } catch {
          // Keep default message.
        }

        throw new Error(errorMessage);
      }

      await response.json();

      setMessage(
        `${artworkRules[type].label} uploaded successfully.`,
      );

      setFile(null);
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Artwork upload failed.",
      );
    } finally {
      setUploading(false);
    }
  }

  const rule = artworkRules[type];

  return (
    <div className="artwork-upload">
      <h3>Artwork Upload</h3>

      <p className="artwork-help">
        Upload artwork for the selected show or episode.
      </p>

      <label htmlFor="artwork-type">
        Artwork Type
      </label>

      <select
        id="artwork-type"
        value={type}
        onChange={(event) =>
          setType(
            event.target.value as ArtworkType,
          )
        }
      >
        <option value="poster">
          Poster — 600 × 900 px
        </option>

        <option value="banner">
          Banner — 1280 × 720 px
        </option>

        <option value="thumbnail">
          Thumbnail — 640 × 360 px
        </option>
      </select>

      <div className="artwork-rule">
        <strong>{rule.label}</strong>

        <span>
          Required dimensions: {rule.dimensions}
        </span>

        <span>
          Maximum file size: 200 KB
        </span>
      </div>

      <label htmlFor="artwork-file">
        Artwork File
      </label>

      <input
        id="artwork-file"
        type="file"
        accept="image/jpeg,image/png,image/webp"
        onChange={(event) =>
          setFile(
            event.target.files?.[0] || null,
          )
        }
      />

      {file && (
        <p className="selected-file">
          Selected: {file.name}
        </p>
      )}

      {error && (
        <div className="artwork-error">
          {error}
        </div>
      )}

      {message && (
        <div className="artwork-success">
          {message}
        </div>
      )}

      <button
        type="button"
        onClick={handleUpload}
        disabled={uploading || !file}
      >
        {uploading
          ? "Uploading..."
          : "Upload Artwork"}
      </button>
    </div>
  );
}