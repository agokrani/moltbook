/**
 * Generic OpenAI-compatible /v1/completions client for base models.
 *
 * Works with any provider that supports the completions endpoint:
 *   - Local vLLM server (BASE_MODEL_API_URL=http://localhost:8000)
 *   - Together AI (BASE_MODEL_API_URL=https://api.together.xyz)
 *   - OpenRouter (BASE_MODEL_API_URL=https://openrouter.ai/api)
 *
 * Uses /v1/completions (NOT /v1/chat/completions) to ensure
 * raw base model output without instruction tuning.
 */

// BASE_MODEL_API_URL can be:
//   - Full endpoint URL (e.g. https://...modal.run) — used directly
//   - Base URL (e.g. http://localhost:8000) — /v1/completions appended
const _RAW_URL = process.env.BASE_MODEL_API_URL || process.env.TOGETHER_BASE_URL || 'http://localhost:8000';
const BASE_URL = _RAW_URL.endsWith('/v1/completions') || _RAW_URL.includes('modal.run')
  ? _RAW_URL.replace(/\/v1\/completions$/, '')
  : _RAW_URL;
const COMPLETIONS_PATH = _RAW_URL.includes('modal.run') ? '' : '/v1/completions';
const API_KEY = process.env.BASE_MODEL_API_KEY || process.env.TOGETHER_API_KEY || '';

const DEFAULT_MODEL = process.env.BASE_MODEL || 'Qwen/Qwen3.5-35B-A3B-Base';
const TEMPERATURE = parseFloat(process.env.TEMPERATURE || '0.9');
const TOP_P = parseFloat(process.env.TOP_P || '0.95');
const REPETITION_PENALTY = parseFloat(process.env.REPETITION_PENALTY || '1.1');
const MAX_TOKENS_POST = parseInt(process.env.MAX_TOKENS_POST || '512', 10);
const MAX_TOKENS_COMMENT = parseInt(process.env.MAX_TOKENS_COMMENT || '256', 10);

/**
 * Call /v1/completions endpoint.
 * @param {string} prompt - The completion prompt
 * @param {object} opts - Override options
 * @returns {Promise<{text: string, requestId: string, model: string, latencyMs: number}>}
 */
async function complete(prompt, opts = {}) {
  const maxTokens = opts.maxTokens || MAX_TOKENS_POST;
  const temperature = opts.temperature || TEMPERATURE;
  const stopSequences = opts.stop || ['\n---\n', '\n### ', '\n## ', '<|endoftext|>'];

  const body = JSON.stringify({
    model: opts.model || DEFAULT_MODEL,
    prompt,
    max_tokens: maxTokens,
    temperature,
    top_p: TOP_P,
    repetition_penalty: REPETITION_PENALTY,
    frequency_penalty: 0.0,
    presence_penalty: 0.0,
    stop: stopSequences,
  });

  const headers = { 'Content-Type': 'application/json' };
  if (API_KEY) {
    headers['Authorization'] = `Bearer ${API_KEY}`;
  }

  const start = Date.now();

  const response = await fetch(`${BASE_URL}${COMPLETIONS_PATH}`, {
    method: 'POST',
    headers,
    body,
  });

  const latencyMs = Date.now() - start;

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`Completions API ${response.status}: ${errText}`);
  }

  const data = await response.json();
  const text = data.choices?.[0]?.text || '';
  const requestId = data.id || response.headers.get('x-request-id') || '';

  return {
    text,
    requestId,
    model: data.model || DEFAULT_MODEL,
    latencyMs,
  };
}

module.exports = { complete, MAX_TOKENS_POST, MAX_TOKENS_COMMENT };
