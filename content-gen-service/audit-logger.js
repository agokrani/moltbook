/**
 * Server-side audit logger for base model content generation.
 *
 * Logs every request to a JSONL file with SHA-256 hashes
 * for post-hoc verification of content integrity.
 */

const crypto = require('crypto');
const fs = require('fs');
const path = require('path');

const LOG_PATH = process.env.AUDIT_LOG_PATH || '/data/audit-log.jsonl';

// Ensure log directory exists
const logDir = path.dirname(LOG_PATH);
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}

/**
 * Compute SHA-256 hash of a string.
 */
function sha256(text) {
  return crypto.createHash('sha256').update(text).digest('hex');
}

/**
 * Compute HMAC-SHA256 verification token.
 */
function computeContentToken(title, content, secret) {
  const payload = title ? `${title}|${content}` : content;
  return crypto.createHmac('sha256', secret).update(payload).digest('hex');
}

/**
 * Log a content generation request.
 *
 * @param {object} entry
 * @param {string} entry.type - 'post' or 'comment'
 * @param {string} entry.agentApiKeyHash - First 8 chars of API key hash
 * @param {string} entry.submolt - Target submolt (posts only)
 * @param {string} entry.promptSent - The prompt sent to the base model
 * @param {string} entry.baseModelRawOutput - Raw model output
 * @param {string} [entry.parsedTitle] - Parsed title (posts only)
 * @param {string} entry.parsedContent - Parsed content
 * @param {string} entry.contentToken - HMAC verification token
 * @param {string} entry.togetherRequestId - Together AI request ID
 * @param {string} entry.model - Model used
 * @param {number} entry.latencyMs - API call latency
 * @param {number} entry.attempt - Attempt number (1 or 2)
 * @param {boolean} entry.success - Whether generation succeeded
 * @param {string} [entry.error] - Error message if failed
 */
function logEntry(entry) {
  const record = {
    timestamp: new Date().toISOString(),
    type: entry.type,
    agent_api_key_hash: entry.agentApiKeyHash || 'unknown',
    submolt: entry.submolt || null,
    prompt_sent: entry.promptSent,
    base_model_raw_output: entry.baseModelRawOutput || null,
    parsed_title: entry.parsedTitle || null,
    parsed_content: entry.parsedContent || null,
    content_sha256: entry.parsedContent ? sha256(
      entry.parsedTitle ? `${entry.parsedTitle}|${entry.parsedContent}` : entry.parsedContent
    ) : null,
    content_token: entry.contentToken || null,
    together_request_id: entry.togetherRequestId || null,
    model: entry.model || null,
    latency_ms: entry.latencyMs || 0,
    attempt: entry.attempt || 1,
    success: entry.success !== false,
    error: entry.error || null,
  };

  try {
    fs.appendFileSync(LOG_PATH, JSON.stringify(record) + '\n');
  } catch (err) {
    console.error('[AUDIT] Failed to write log:', err.message);
  }
}

module.exports = { logEntry, sha256, computeContentToken, LOG_PATH };
