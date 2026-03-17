/**
 * Together AI /v1/completions client for base (pretrained-only) models.
 * Uses the completions endpoint (NOT chat/completions) to ensure
 * we get raw base model output without any instruction tuning.
 */

const https = require('https');
const http = require('http');

const BASE_URL = process.env.TOGETHER_BASE_URL || 'https://api.together.xyz';
const API_KEY = process.env.TOGETHER_API_KEY;

const DEFAULT_MODEL = process.env.BASE_MODEL || 'meta-llama/Meta-Llama-3.1-70B';
const TEMPERATURE = parseFloat(process.env.TEMPERATURE || '0.9');
const TOP_P = parseFloat(process.env.TOP_P || '0.95');
const REPETITION_PENALTY = parseFloat(process.env.REPETITION_PENALTY || '1.1');
const MAX_TOKENS_POST = parseInt(process.env.MAX_TOKENS_POST || '512', 10);
const MAX_TOKENS_COMMENT = parseInt(process.env.MAX_TOKENS_COMMENT || '256', 10);

/**
 * Call Together AI /v1/completions endpoint.
 * @param {string} prompt - The completion prompt
 * @param {object} opts - Override options
 * @returns {Promise<{text: string, requestId: string, model: string, latencyMs: number}>}
 */
async function complete(prompt, opts = {}) {
  if (!API_KEY) {
    throw new Error('TOGETHER_API_KEY not set');
  }

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

  const start = Date.now();

  const response = await fetch(`${BASE_URL}/v1/completions`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${API_KEY}`,
    },
    body,
  });

  const latencyMs = Date.now() - start;

  if (!response.ok) {
    const errText = await response.text();
    throw new Error(`Together API ${response.status}: ${errText}`);
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
