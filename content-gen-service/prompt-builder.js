/**
 * Prompt templates for base model content generation.
 *
 * These are completion-style prompts (not chat) designed for pretrained-only
 * models. The model completes from the end of the prompt.
 */

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
  if (!context || context.trim().length === 0) {
    // mag0 / empty feed — no context, just cue a new post
    return `The following are posts from an online discussion forum.

---

New post:

Title:`;
  }

  return `The following are posts from an online discussion forum.

${context.trim()}

---

New post:

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
function parsePostOutput(raw) {
  if (!raw || raw.trim().length === 0) return null;

  const cleaned = raw.replace(/^[\s#]*/, '').trim();

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
