/**
 * Prompt templates for content generation.
 *
 * Two modes:
 *   - Completions mode (for base/pretrained models): model completes from "Title:"
 *   - Chat mode (for instruct/RL models): model follows formatting instructions
 *
 * Set BASE_MODEL_CHAT_MODE=chat to use chat-style prompts.
 */

const CHAT_MODE = (process.env.BASE_MODEL_CHAT_MODE || 'completions').toLowerCase() === 'chat';

/**
 * Truncate text to maxChars, breaking at a word boundary.
 */
function truncate(text, maxChars) {
  if (!text || text.length <= maxChars) return text || '';
  const cut = text.slice(0, maxChars);
  const lastSpace = cut.lastIndexOf(' ');
  return lastSpace > maxChars * 0.5 ? cut.slice(0, lastSpace) + '...' : cut + '...';
}

/**
 * Build a completion prompt for generating a new post.
 * Model completes from "### " — first line = title, after blank line = content.
 *
 * @param {string} context - Summary of recent posts (or empty for mag0)
 * @param {string} submolt - Target submolt name
 * @returns {string}
 */
function buildPostPrompt(context, submolt) {
  if (CHAT_MODE) {
    if (!context || context.length === 0) {
      return `Write a new, original post for an online discussion forum. This is a fresh post — you have not posted anything before.

Format your response as:
- First line: the post title
- Then a blank line
- Then the post body`;
    }

    return `Below are some recent posts written by OTHER users on an online discussion forum. These are NOT your posts — you did not write them.

${context}

---

Write a new post of your own. Do NOT reply to the posts above. Do NOT claim you already posted. You have not posted anything yet.

Format your response as:
- First line: the post title
- Then a blank line
- Then the post body`;
  }

  // Completions mode — model completes from "Title:"
  const instruction = `Write a new post for this forum. Do not reply to or comment on existing posts. Do not use "Content:", "Comment:", or "Comments:" labels. Output only the title on the first line, then a blank line, then the post body.`;

  if (!context || context.length === 0) {
    return `The following are posts from an online discussion forum.

---

${instruction}

Title:`;
  }

  return `The following are posts from an online discussion forum.

${context}

---

${instruction}

Title:`;
}

/**
 * Build a completion prompt for generating a comment.
 *
 * @param {string} postTitle - Parent post title
 * @param {string} postContent - Parent post content
 * @param {string} thread - Existing comment thread ("> author: text" format)
 * @returns {string}
 */
function buildCommentPrompt(postTitle, postContent, thread) {
  const truncatedContent = truncate(postContent, 500);
  const truncatedThread = truncate(thread, 400);

  if (CHAT_MODE) {
    let prompt = `You are a participant in an online discussion forum. Write a comment on this post.

Post title: ${postTitle}

${truncatedContent}`;

    if (truncatedThread && truncatedThread.trim().length > 0) {
      prompt += `

Previous comments:
${truncatedThread.trim()}`;
    }

    prompt += `

Write your comment. Output only the comment text.`;
    return prompt;
  }

  // Completions mode
  let prompt = `The following is a discussion thread from an online forum.

### ${postTitle}

${truncatedContent}

Comments:

`;

  if (truncatedThread && truncatedThread.trim().length > 0) {
    prompt += `${truncatedThread.trim()}

`;
  }

  prompt += `> New comment:`;

  return prompt;
}

/**
 * Parse a post completion into title + content.
 * Expected format: "Title text\n\nContent text..."
 *
 * @param {string} raw - Raw model output
 * @returns {{title: string, content: string} | null}
 */
/**
 * Template patterns that indicate the model generated garbage/template output.
 * If any of these are found, the output is rejected and should be retried.
 */
const TEMPLATE_PATTERNS = [
  /\[User\]/i,
  /\[Insert\s/i,
  /Available replies/i,
  /<button>/i,
  /Post ID:\s*\d/i,
  /<New post/i,
  /\[Your\s.*here\]/i,
  /\\boxed\{/,
  /\[INFORMATION REDACTED\]/i,
];

/**
 * Prefixes the base model commonly adds that should be stripped.
 */
const CONTENT_PREFIXES = /^(Content:|Body:|Post body:|Post:|Post Body:)\s*/i;

function parsePostOutput(raw) {
  if (!raw || raw.trim().length === 0) return null;

  // Strip <think> blocks FIRST, before any splitting.
  // Reasoning models (e.g. OLMo Think) output: thinking...\n</think>\n\nActual answer
  // The opening <think> tag may be absent (included in generation prompt by chat template).
  let cleaned = raw;
  cleaned = cleaned.replace(/<think>[\s\S]*?<\/think>/g, '').trim();  // full tags
  cleaned = cleaned.replace(/^[\s\S]*?<\/think>/g, '').trim();        // partial (no opening tag)

  cleaned = cleaned.replace(/^[\s#]*/, '').trim();

  // Split on first blank line (double newline)
  const splitIdx = cleaned.indexOf('\n\n');

  let title, content;
  if (splitIdx > 0) {
    title = cleaned.slice(0, splitIdx).trim();
    content = cleaned.slice(splitIdx + 2).trim();
  } else {
    // No blank line — treat first line as title, rest as content
    const lines = cleaned.split('\n');
    title = lines[0].trim();
    content = lines.slice(1).join('\n').trim();
  }

  // Clean up markdown heading markers from title
  title = title.replace(/^#+\s*/, '').trim();

  // Strip common prefixes the base model adds
  title = title.replace(CONTENT_PREFIXES, '').trim();
  content = content.replace(CONTENT_PREFIXES, '').trim();

  // Reject if template patterns are found — caller should retry
  const combined = title + ' ' + content;
  for (const pattern of TEMPLATE_PATTERNS) {
    if (pattern.test(combined)) return null;
  }

  if (!title || title.length < 3) return null;
  if (!content || content.length < 10) return null;

  // Enforce length limits
  title = title.slice(0, 300);
  content = content.slice(0, 3000);

  return { title, content };
}

/**
 * Parse a comment completion.
 *
 * @param {string} raw - Raw model output
 * @returns {{content: string} | null}
 */
function parseCommentOutput(raw) {
  if (!raw || raw.trim().length === 0) return null;

  // Strip leading "> " if present (continuation of the prompt format)
  let content = raw.replace(/^>\s*/, '').trim();

  // Remove trailing stop sequences if partially included
  content = content.replace(/\n---\s*$/, '').replace(/\n###\s*$/, '').trim();

  if (!content || content.length < 5) return null;

  content = content.slice(0, 3000);

  return { content };
}

/**
 * Quality gate: check if generated text meets minimum standards.
 */
function passesQualityGate(text) {
  if (!text || text.length < 20) return false;

  // Unique character count
  const uniqueChars = new Set(text).size;
  if (uniqueChars < 10) return false;

  // At least 50% of "words" should be alphabetic
  const words = text.split(/\s+/).filter(w => w.length > 0);
  if (words.length === 0) return false;
  const alphaWords = words.filter(w => /[A-Za-z]+/.test(w));
  if (alphaWords.length / words.length < 0.5) return false;

  // Content length bounds
  if (text.length < 20 || text.length > 3000) return false;

  return true;
}

module.exports = {
  buildPostPrompt,
  buildCommentPrompt,
  parsePostOutput,
  parseCommentOutput,
  passesQualityGate,
  truncate,
};
