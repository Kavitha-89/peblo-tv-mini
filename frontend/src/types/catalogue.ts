export interface Artwork {
  type: "poster" | "banner" | "thumbnail";
  url: string;
  width?: number;
  height?: number;
}

export interface ArtworkMap {
  poster?: string;
  banner?: string;
  thumbnail?: string;
}

export interface EpisodeVariant {
  episode_id?: string;
  title: string;
  language: string;
  duration_seconds: number;
  artwork?: ArtworkMap;
}

export interface CatalogueEpisode {
  episode_id?: string;
  title: string;
  description?: string;
  season_number?: number;
  episode_number: number;
  content_group: string;
  languages: string[];
  duration_seconds: number;
  artwork?: ArtworkMap;
  variants: EpisodeVariant[];
}

export interface CatalogueSeason {
  season_number: number;
  title?: string;
  episodes: CatalogueEpisode[];
}

export interface CatalogueShow {
  show_id: number;
  slug: string;
  title: string;
  description?: string;
  section: string;
  categories: string[];
  artwork?: ArtworkMap;
  seasons: CatalogueSeason[];
}

export interface CatalogueResponse {
  version: number;
  generated_at?: string;
  shows: CatalogueShow[];
}

export interface SearchResponse {
  count: number;
  results: CatalogueShow[];
}