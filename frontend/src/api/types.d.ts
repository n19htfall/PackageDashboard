interface Package {
    /** Purl */
    purl: string;
    /** Name */
    name: string;
    /** Version */
    version?: string;
    /** Summary */
    summary?: string;
    /** Description */
    description?: string;
    /** License */
    license?: string;
    /** Homepage Url */
    homepage_url?: string;
    /** Repo Url */
    repo_url?: string;
    /** Source Purl */
    source_purl?: string;
    /** Distro */
    distro?: string;
    /** Distro Release */
    distro_release?: string;
    /** Arch */
    arch?: string;
    /** Source Pid */
    source_pid?: string;
    /**
     * Record Created At 
     * Format: date-time 
     * @default 2023-07-02T08:08:09.513451
     */
    record_created_at?: string;
    /**
     * Record Updated At 
     * Format: date-time 
     * @default 2023-07-02T08:08:09.513454
     */
    record_updated_at?: string;
};

/**
 * PackageDependency 
 * @description Defines a software package (can be rpm/npm/maven/etc.)
 * This is not the result of the package scan
 */
interface PackageDependency {
    /** Purl */
    purl: string;
    /** Pkgid */
    pkgid?: number;
    /** Dep Purl */
    dep_purl: string;
    /** Dep Pkgid */
    dep_pkgid?: number;
    /** Type */
    type: string;
    /** Constraint */
    constraint?: string;
    /**
     * Dep At 
     * Format: date-time 
     * @default 2023-07-02T08:08:09.519286
     */
    dep_at?: string;
};

interface PackageAlert{
    _id: string;
    purl: string;
    repo_url: string;
    name: string;
    version: string;
    commit_sha: string;
    vulns: string[]; // Array of strings
    n_contributors: number;
    is_archived: boolean;
    license_compatibility: number;
    record_created_at: string;
    record_updated_at: string;
}

/**
 * PackageSource 
 * @description Defines a software package (can be rpm/npm/maven/etc.)
 * This is not the result of the package scan
 */
interface PackageSource {
    /** Purl */
    purl: string;
    /** Repo Url */
    repo_url: string;
    /** Type */
    type: string;
    /**
     * Sourced At 
     * Format: date-time 
     * @default 2023-07-02T08:08:09.520313
     */
    sourced_at?: string;
    confidence?: number;
};
/**
 * PackageStats 
 * @description The calculated statistics of a repository
 */
interface PackageStats {
    /** Url */
    url: string;
    /**
     * Stats From 
     * Format: date-time
     */
    stats_from: string;
    /**
     * Stats Interval 
     * @enum {string}
     */
    stats_interval: "Day" | "Week" | "Month" | "Year";
    /**
     * Record Created At 
     * Format: date-time 
     * @default 2023-07-02T08:08:09.514983
     */
    record_created_at?: string;
    /**
     * Record Updated At 
     * Format: date-time 
     * @default 2023-07-02T08:08:09.514983
     */
    record_updated_at?: string;
    /** N Commits */
    n_commits: number;
    /** N Comments */
    n_comments: number;
    /** N Issues */
    n_issues: number;
    /** N Prs */
    n_prs: number;
    /** N Stars */
    n_stars: number;
    /** N Tags */
    n_tags: number;
    /** Pagerank */
    pagerank?: number;
};

/**
 * Repository 
 * @description Defines a software repository from code-hosting sites (e.g. github.com, gitee.com)
 * Data from API goes here
 */
interface Repository {
    /** Id */
    _id?: string;
    /** Url */
    url: string;
    /** Name */
    name: string;
    /** N Stars */
    n_stars: number;
    /**
     * Created At 
     * Format: date-time
     */
    created_at: string;
    /**
     * Updated At 
     * Format: date-time
     */
    updated_at: string;
    /**
     * Pushed At 
     * Format: date-time
     */
    pushed_at: string;
    /**
     * Archived At 
     * Format: date-time
     */
    archived_at?: string;
    /** Is Template */
    is_template: boolean;
    /** Is Fork */
    is_fork: boolean;
    /** Primary Language */
    primary_language?: string;
    /**
     * Topics 
     * @default []
     */
    topics?: (string)[];
    /** Description */
    description?: string;
    /** License */
    license?: string;
    /**
     * Record Created At 
     * Format: date-time 
     * @default 2023-07-02T08:08:09.516355
     */
    record_created_at?: string;
    /**
     * Record Updated At 
     * Format: date-time 
     * @default 2023-07-02T08:08:09.516356
     */
    record_updated_at?: string;
};

/**
 * RepositoryStats 
 * @description The calculated statistics of a repository
 */
interface RepositoryStats {
    /** Url */
    url: string;
    /**
     * Stats From 
     * Format: date-time
     */
    stats_from: string;
    /**
     * Stats Interval 
     * @enum {string}
     */
    stats_interval: "Day" | "Week" | "Month" | "Year";
    /** N Commits */
    n_commits: number;
    /** N Comments */
    n_comments: number;
    /** N Issues */
    n_issues: number;
    /** N Prs */
    n_prs: number;
    /** N Stars */
    n_stars: number;
    /** N Tags */
    n_tags: number;
    /**
     * Record Created At 
     * Format: date-time 
     * @default 2023-07-02T08:08:09.517765
     */
    record_created_at?: string;
    /**
     * Record Updated At 
     * Format: date-time 
     * @default 2023-07-02T08:08:09.517766
     */
    record_updated_at?: string;
    /** Hits */
    hits?: number;
    /** Hits Rank Pct */
    hits_rank_pct?: number;
    /** Hits Zscore */
    hits_zscore?: number;
};

/** ValidationError */
interface ValidationError {
    /** Location */
    loc: (string | number)[];
    /** Message */
    msg: string;
    /** Error Type */
    type: string;
};

/** Page */
interface Page<T> {
    /** Items */
    items: T[];
    /** Total */
    total: number;
    /** Page */
    page?: number;
    /** Size */
    size?: number;
    /** Pages */
    pages?: number;
  };