// Frontend configuration constants

// API Configuration
export const API_TIMEOUT_MS = 60_000;
export const MAX_RETRIES = 3;

// Polling Configuration
export const INJECTION_POLL_INTERVAL_MS = 3_000;
export const INJECTION_MAX_ATTEMPTS = 40;
export const INJECTION_POLL_BACKOFF_FACTOR = 1.5;
export const INJECTION_POLL_MAX_DELAY_MS = 10_000;

// Upload Configuration
export const MAX_STATUS_POLL_ATTEMPTS = 60;
export const STATUS_POLL_BACKOFF_FACTOR = 1.5;

// Event Names
export const EVENT_RATE_LIMIT_START = 'med-parser-rate-limit';
export const EVENT_RATE_LIMIT_END = 'med-parser-rate-limit-end';
