// Frontend configuration constants

// API Configuration
export const API_TIMEOUT_MS = 60_000; // 60 seconds
export const MAX_RETRIES = 3;
export const BASE_RETRY_DELAY_MS = 1000;

// Polling Configuration
export const HEALTH_CHECK_INTERVAL_MS = 10_000; // 10 seconds
export const STATS_POLL_INTERVAL_MS = 30_000; // 30 seconds
export const OPS_FEED_POLL_INTERVAL_MS = 5_000; // 5 seconds
export const INJECTION_POLL_INTERVAL_MS = 3_000; // 3 seconds (initial)
export const INJECTION_MAX_ATTEMPTS = 40;
export const INJECTION_POLL_BACKOFF_FACTOR = 1.5;
export const INJECTION_POLL_MAX_DELAY_MS = 10_000;

// Upload Configuration
export const MAX_STATUS_POLL_ATTEMPTS = 60;
export const STATUS_POLL_BACKOFF_FACTOR = 1.5;

// Event Names
export const EVENT_RATE_LIMIT_START = 'med-parser-rate-limit';
export const EVENT_RATE_LIMIT_END = 'med-parser-rate-limit-end';
export const EVENT_OPS_FEED_SEARCH = 'ops-feed-search';

// Validation Patterns
export const DEA_REGEX = /^[A-Z]{2}\d{7}$/;
export const DATE_REGEX = /^\d{4}-\d{2}-\d{2}$|^\d{2}\/\d{2}\/\d{4}$/;
export const NDC_REGEX = /^\d{5}-\d{4}-\d{2}$|^\d{5}-\d{3}-\d{2}$/;
