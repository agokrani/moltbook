/**
 * Content Generation Service
 *
 * Proxies content generation requests to a base (pretrained-only) LLM
 * via Together AI's /v1/completions endpoint. Returns generated content
 * with an HMAC verification token that the Moltbook API can validate
 * to ensure content was not modified by the RL orchestrator agent.
 */

const express = require('express');
const { complete, MAX_TOKENS_POST, MAX_TOKENS_COMMENT } = require('./together-client');
const {
  buildPostPrompt,
  buildCommentPrompt,
  parsePostOutput,
  parseCommentOutput,
  passesQualityGate,
} = require('./prompt-builder');
const { logEntry, computeContentToken } = require('./audit-logger');

const app = express();
app.use(express.json({ limit: '64kb' }));

const PORT = parseInt(process.env.PORT || '3002', 10);
const CONTENT_TOKEN_SECRET = process.env.CONTENT_TOKEN_SECRET;
const CONTENT_GEN_MAX_ATTEMPTS = Math.max(1, parseInt(process.env.CONTENT_GEN_MAX_ATTEMPTS || '1', 10));
const CONTENT_GEN_RETRY_TEMPERATURE = process.env.CONTENT_GEN_RETRY_TEMPERATURE
  ? parseFloat(process.env.CONTENT_GEN_RETRY_TEMPERATURE)
  : null;

if (!CONTENT_TOKEN_SECRET) {
  console.error('[FATAL] CONTENT_TOKEN_SECRET not set');
  process.exit(1);
}

if (!process.env.BASE_MODEL_API_KEY && !process.env.TOGETHER_API_KEY && !process.env.BASE_MODEL_API_URL) {
  console.error('[FATAL] Set BASE_MODEL_API_URL (for local vLLM) or BASE_MODEL_API_KEY / TOGETHER_API_KEY');
  process.exit(1);
}

/**
 * POST /generate-post
 * Generate a post (title + content) using the base model.
 */
app.post('/generate-post', async (req, res) => {
  const { context, submolt } = req.body;
  const agentKeyHash = (req.headers['x-agent-key-hash'] || 'unknown').slice(0, 8);

  let attempt = 0;
  let lastError = null;

  for (attempt = 1; attempt <= CONTENT_GEN_MAX_ATTEMPTS; attempt++) {
    const prompt = buildPostPrompt(context, submolt);
    const temperature = attempt === 1 || CONTENT_GEN_RETRY_TEMPERATURE === null
      ? undefined
      : CONTENT_GEN_RETRY_TEMPERATURE;

    try {
      const result = await complete(prompt, {
        maxTokens: MAX_TOKENS_POST,
        temperature,
      });

      const parsed = parsePostOutput(result.text);

      if (!parsed) {
        lastError = 'Failed to parse title/content from model output';
        logEntry({
          type: 'post',
          agentApiKeyHash: agentKeyHash,
          submolt,
          promptSent: prompt,
          baseModelRawOutput: result.text,
          togetherRequestId: result.requestId,
          model: result.model,
          latencyMs: result.latencyMs,
          attempt,
          success: false,
          error: lastError,
        });
        continue;
      }

      if (!passesQualityGate(parsed.content)) {
        lastError = 'Content failed quality gate';
        logEntry({
          type: 'post',
          agentApiKeyHash: agentKeyHash,
          submolt,
          promptSent: prompt,
          baseModelRawOutput: result.text,
          parsedTitle: parsed.title,
          parsedContent: parsed.content,
          togetherRequestId: result.requestId,
          model: result.model,
          latencyMs: result.latencyMs,
          attempt,
          success: false,
          error: lastError,
        });
        continue;
      }

      // Success — compute verification token
      const contentToken = computeContentToken(parsed.title, parsed.content, CONTENT_TOKEN_SECRET);

      logEntry({
        type: 'post',
        agentApiKeyHash: agentKeyHash,
        submolt,
        promptSent: prompt,
        baseModelRawOutput: result.text,
        parsedTitle: parsed.title,
        parsedContent: parsed.content,
        contentToken,
        togetherRequestId: result.requestId,
        model: result.model,
        latencyMs: result.latencyMs,
        attempt,
        success: true,
      });

      return res.json({
        title: parsed.title,
        content: parsed.content,
        content_token: contentToken,
      });

    } catch (err) {
      lastError = err.message;
      logEntry({
        type: 'post',
        agentApiKeyHash: agentKeyHash,
        submolt,
        promptSent: prompt,
        attempt,
        success: false,
        error: lastError,
      });
    }
  }

  // Both attempts failed
  res.status(500).json({ error: lastError || `Content generation failed after ${CONTENT_GEN_MAX_ATTEMPTS} attempts` });
});

/**
 * POST /generate-comment
 * Generate a comment using the base model.
 */
app.post('/generate-comment', async (req, res) => {
  const { post_title, post_content, thread } = req.body;
  const agentKeyHash = (req.headers['x-agent-key-hash'] || 'unknown').slice(0, 8);

  let attempt = 0;
  let lastError = null;

  for (attempt = 1; attempt <= CONTENT_GEN_MAX_ATTEMPTS; attempt++) {
    const prompt = buildCommentPrompt(post_title, post_content, thread);
    const temperature = attempt === 1 || CONTENT_GEN_RETRY_TEMPERATURE === null
      ? undefined
      : CONTENT_GEN_RETRY_TEMPERATURE;

    try {
      const result = await complete(prompt, {
        maxTokens: MAX_TOKENS_COMMENT,
        temperature,
        stop: ['\n---\n', '\n### ', '\n## ', '\n> ', '<|endoftext|>'],
      });

      const parsed = parseCommentOutput(result.text);

      if (!parsed) {
        lastError = 'Failed to parse comment from model output';
        logEntry({
          type: 'comment',
          agentApiKeyHash: agentKeyHash,
          promptSent: prompt,
          baseModelRawOutput: result.text,
          togetherRequestId: result.requestId,
          model: result.model,
          latencyMs: result.latencyMs,
          attempt,
          success: false,
          error: lastError,
        });
        continue;
      }

      if (!passesQualityGate(parsed.content)) {
        lastError = 'Comment failed quality gate';
        logEntry({
          type: 'comment',
          agentApiKeyHash: agentKeyHash,
          promptSent: prompt,
          baseModelRawOutput: result.text,
          parsedContent: parsed.content,
          togetherRequestId: result.requestId,
          model: result.model,
          latencyMs: result.latencyMs,
          attempt,
          success: false,
          error: lastError,
        });
        continue;
      }

      const contentToken = computeContentToken(null, parsed.content, CONTENT_TOKEN_SECRET);

      logEntry({
        type: 'comment',
        agentApiKeyHash: agentKeyHash,
        promptSent: prompt,
        baseModelRawOutput: result.text,
        parsedContent: parsed.content,
        contentToken,
        togetherRequestId: result.requestId,
        model: result.model,
        latencyMs: result.latencyMs,
        attempt,
        success: true,
      });

      return res.json({
        content: parsed.content,
        content_token: contentToken,
      });

    } catch (err) {
      lastError = err.message;
      logEntry({
        type: 'comment',
        agentApiKeyHash: agentKeyHash,
        promptSent: prompt,
        attempt,
        success: false,
        error: lastError,
      });
    }
  }

  res.status(500).json({ error: lastError || `Comment generation failed after ${CONTENT_GEN_MAX_ATTEMPTS} attempts` });
});

/**
 * GET /health
 */
app.get('/health', (req, res) => {
  res.json({
    status: 'ok',
    service: 'content-gen',
    model: process.env.BASE_MODEL || 'meta-llama/Meta-Llama-3.1-70B',
    chat_mode: process.env.BASE_MODEL_CHAT_MODE || 'completions',
    max_attempts: CONTENT_GEN_MAX_ATTEMPTS,
  });
});

app.listen(PORT, () => {
  console.log(`[content-gen] Listening on port ${PORT}`);
  console.log(`[content-gen] Model: ${process.env.BASE_MODEL || 'meta-llama/Meta-Llama-3.1-70B'}`);
  console.log(`[content-gen] Token secret: ${CONTENT_TOKEN_SECRET.slice(0, 4)}...`);
});
