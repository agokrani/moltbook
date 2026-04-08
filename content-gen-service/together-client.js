/**
 * Content generation client that supports two modes:
 *
 * 1. COMPLETIONS mode (for base models):
 *    - Uses /v1/completions endpoint
 *    - Works with Modal/SGLang, vLLM, Together AI
 *    - Sends raw prompt, model completes it
 *
 * 2. CHAT mode (for instruct/RL models via OpenRouter):
 *    - Uses /v1/chat/completions endpoint
 *    - Works with OpenRouter, OpenAI, etc.
 *    - Sends prompt as a user message
 *
 * Set BASE_MODEL_MODE=chat to use chat mode.
 * Default is completions mode.
 */

const _RAW_URL = process.env.BASE_MODEL_API_URL || process.env.TOGETHER_BASE_URL || 'http://localhost:8000';
const API_KEY = process.env.BASE_MODEL_API_KEY || process.env.TOGETHER_API_KEY || '';
const MODE = (process.env.BASE_MODEL_CHAT_MODE || 'completions').toLowerCase();

// URL handling
const IS_MODAL = _RAW_URL.includes('modal.run');
const BASE_URL = IS_MODAL ? _RAW_URL : _RAW_URL.replace(/\/v1\/(completions|chat\/completions)$/, '');
const COMPLETIONS_PATH = IS_MODAL ? '' : (MODE === 'chat' ? '/v1/chat/completions' : '/v1/completions');

const DEFAULT_MODEL = process.env.BASE_MODEL || 'Qwen/Qwen3.5-35B-A3B-Base';
const TEMPERATURE = parseFloat(process.env.TEMPERATURE || '0.9');
const TOP_P = parseFloat(process.env.TOP_P || '0.95');
const REPETITION_PENALTY = parseFloat(process.env.REPETITION_PENALTY || '1.1');
// NOTE: Must leave room for the prompt + chat template overhead within
// the model's context length. max_tokens is dynamically capped based on
// prompt size to avoid context-length errors.
const MAX_TOKENS_POST = parseInt(process.env.MAX_TOKENS_POST || '28000', 10);
const MAX_TOKENS_COMMENT = parseInt(process.env.MAX_TOKENS_COMMENT || '14000', 10);
const MODEL_CONTEXT_LENGTH = parseInt(process.env.MODEL_CONTEXT_LENGTH || '32768', 10);
const CHAT_TEMPLATE_OVERHEAD_TOKENS = 200;  // safety margin for chat template + system msg

/**
 * Generate a completion using either completions or chat API.
 * @param {string} prompt - The prompt text
 * @param {object} opts - Override options
 * @returns {Promise<{text: string, requestId: string, model: string, latencyMs: number}>}
 */
async function complete(prompt, opts = {}) {
  const temperature = opts.temperature || TEMPERATURE;
  const stopSequences = opts.stop || ['\n---\n', '\n### ', '\n## ', '<|endoftext|>', '\n\nTitle:', '\nTitle:'];

  // Estimate prompt tokens (rough: ~4 chars per token for English text)
  // and dynamically cap max_tokens so prompt + output fits the context window.
  const estimatedPromptTokens = Math.ceil(prompt.length / 4);
  const availableOutputTokens = MODEL_CONTEXT_LENGTH - estimatedPromptTokens - CHAT_TEMPLATE_OVERHEAD_TOKENS;
  const requestedMaxTokens = opts.maxTokens || MAX_TOKENS_POST;
  const maxTokens = Math.max(512, Math.min(requestedMaxTokens, availableOutputTokens));

  let body;

  if (MODE === 'chat') {
    // Chat completions mode — send prompt as user message
    body = JSON.stringify({
      model: opts.model || DEFAULT_MODEL,
      messages: [
        { role: 'user', content: prompt }
      ],
      max_tokens: maxTokens,
      temperature,
      top_p: TOP_P,
      stop: stopSequences,
    });
  } else {
    // Completions mode — raw prompt completion
    body = JSON.stringify({
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
  }

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
    throw new Error(`${MODE === 'chat' ? 'Chat' : 'Completions'} API ${response.status}: ${errText}`);
  }

  const data = await response.json();

  // Extract text from either response format
  let text;
  if (MODE === 'chat') {
    text = data.choices?.[0]?.message?.content || '';
  } else {
    text = data.choices?.[0]?.text || '';
  }

  const requestId = data.id || response.headers.get('x-request-id') || '';

  return {
    text,
    requestId,
    model: data.model || DEFAULT_MODEL,
    latencyMs,
  };
}

module.exports = { complete, MAX_TOKENS_POST, MAX_TOKENS_COMMENT, MODE };
