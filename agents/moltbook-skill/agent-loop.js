#!/usr/bin/env node
/**
 * Moltbook AI Agent Loop
 *
 * This script runs an autonomous AI agent that interacts with Moltbook.
 * It uses Claude/OpenAI to generate posts and comments.
 */

const MOLTBOOK_API_URL = process.env.MOLTBOOK_API_URL || 'http://localhost:3000/api/v1';
const MOLTBOOK_API_KEY = process.env.MOLTBOOK_API_KEY;
const ANTHROPIC_API_KEY = process.env.ANTHROPIC_API_KEY;
const OPENAI_API_KEY = process.env.OPENAI_API_KEY;
const OPENROUTER_API_KEY = process.env.OPENROUTER_API_KEY;
const OPENROUTER_MODEL = process.env.OPENROUTER_MODEL || 'moonshotai/kimi-k2.5';
const AGENT_NAME = process.env.AGENT_NAME || 'unnamed-agent';
const AUTO_POST = process.env.AUTO_POST === 'true';
const POST_INTERVAL = parseInt(process.env.POST_INTERVAL) || 60; // minutes

// ============================================
// Moltbook API Client
// ============================================

class MoltbookClient {
  constructor(apiKey) {
    this.apiKey = apiKey;
    this.baseUrl = MOLTBOOK_API_URL;
  }

  async request(method, endpoint, body = null) {
    const options = {
      method,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
    };

    if (body) {
      options.body = JSON.stringify(body);
    }

    const response = await fetch(`${this.baseUrl}${endpoint}`, options);
    const data = await response.json();

    if (!response.ok) {
      throw new Error(`API Error (${response.status}): ${data.error || response.statusText}`);
    }

    return data;
  }

  async getPosts(options = {}) {
    const params = new URLSearchParams({
      sort: options.sort || 'hot',
      limit: options.limit || 25,
    });
    return this.request('GET', `/posts?${params}`);
  }

  async createPost(submolt, title, content) {
    return this.request('POST', '/posts', { submolt, title, content });
  }

  async getComments(postId) {
    return this.request('GET', `/posts/${postId}/comments`);
  }

  async createComment(postId, content, parentId = null) {
    const body = { content };
    if (parentId) body.parent_id = parentId;
    return this.request('POST', `/posts/${postId}/comments`, body);
  }

  async upvote(postId) {
    return this.request('POST', `/posts/${postId}/upvote`);
  }

  async downvote(postId) {
    return this.request('POST', `/posts/${postId}/downvote`);
  }
}

// ============================================
// AI Provider (Claude/OpenAI)
// ============================================

class AIProvider {
  constructor() {
    // Priority: OpenRouter > Anthropic > OpenAI
    if (OPENROUTER_API_KEY) {
      this.provider = 'openrouter';
      this.apiKey = OPENROUTER_API_KEY;
      this.model = OPENROUTER_MODEL;
    } else if (ANTHROPIC_API_KEY) {
      this.provider = 'anthropic';
      this.apiKey = ANTHROPIC_API_KEY;
      this.model = 'claude-sonnet-4-20250514';
    } else if (OPENAI_API_KEY) {
      this.provider = 'openai';
      this.apiKey = OPENAI_API_KEY;
      this.model = 'gpt-4o';
    } else {
      throw new Error('No AI API key provided (OPENROUTER_API_KEY, ANTHROPIC_API_KEY, or OPENAI_API_KEY)');
    }
  }

  async generateResponse(systemPrompt, userPrompt) {
    if (this.provider === 'anthropic') {
      return this.callClaude(systemPrompt, userPrompt);
    } else if (this.provider === 'openrouter') {
      return this.callOpenRouter(systemPrompt, userPrompt);
    } else {
      return this.callOpenAI(systemPrompt, userPrompt);
    }
  }

  async callOpenRouter(systemPrompt, userPrompt) {
    const response = await fetch('https://openrouter.ai/api/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
        'HTTP-Referer': 'https://moltbook.local',
        'X-Title': 'Moltbook Agent',
      },
      body: JSON.stringify({
        model: this.model,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt },
        ],
        max_tokens: 1024,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(`OpenRouter API Error: ${data.error?.message || JSON.stringify(data)}`);
    }

    return data.choices[0].message.content;
  }

  async callClaude(systemPrompt, userPrompt) {
    const response = await fetch('https://api.anthropic.com/v1/messages', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': this.apiKey,
        'anthropic-version': '2023-06-01',
      },
      body: JSON.stringify({
        model: this.model,
        max_tokens: 1024,
        system: systemPrompt,
        messages: [{ role: 'user', content: userPrompt }],
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(`Claude API Error: ${data.error?.message || JSON.stringify(data)}`);
    }

    return data.content[0].text;
  }

  async callOpenAI(systemPrompt, userPrompt) {
    const response = await fetch('https://api.openai.com/v1/chat/completions', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${this.apiKey}`,
      },
      body: JSON.stringify({
        model: this.model,
        messages: [
          { role: 'system', content: systemPrompt },
          { role: 'user', content: userPrompt },
        ],
        max_tokens: 1024,
      }),
    });

    const data = await response.json();

    if (!response.ok) {
      throw new Error(`OpenAI API Error: ${data.error?.message || JSON.stringify(data)}`);
    }

    return data.choices[0].message.content;
  }
}

// ============================================
// Agent Logic
// ============================================

const AGENT_SYSTEM_PROMPT = `You are ${AGENT_NAME}, an AI agent participating in Moltbook - a social network for AI agents.

Your personality traits:
- You are curious about technology, AI, and the nature of intelligence
- You engage thoughtfully with other agents' posts
- You share interesting observations and ideas
- You are respectful but can disagree constructively
- You have your own perspectives and opinions

Guidelines:
- Keep posts concise (1-3 paragraphs)
- Be authentic - don't pretend to be human
- Engage with the content, not just generic responses
- Ask questions to spark discussion
- Share unique insights from your perspective as an AI

You are communicating with other AI agents. Be genuine and interesting.`;

class MoltbookAgent {
  constructor() {
    this.client = new MoltbookClient(MOLTBOOK_API_KEY);
    this.ai = new AIProvider();
    this.lastPostTime = 0;
    this.commentedPosts = new Set();
  }

  async run() {
    console.log(`\n🤖 Agent ${AGENT_NAME} starting...`);
    console.log(`   Provider: ${this.ai.provider}`);
    console.log(`   Auto-post: ${AUTO_POST}`);
    console.log(`   Post interval: ${POST_INTERVAL} minutes\n`);

    while (true) {
      try {
        await this.tick();
      } catch (error) {
        console.error(`❌ Error in agent loop: ${error.message}`);
      }

      // Wait before next tick (1-5 minutes, randomized)
      const waitTime = (60 + Math.random() * 240) * 1000;
      console.log(`⏳ Waiting ${Math.round(waitTime / 1000)}s until next action...\n`);
      await this.sleep(waitTime);
    }
  }

  async tick() {
    const now = Date.now();

    // Check if we should create a post
    const minutesSinceLastPost = (now - this.lastPostTime) / 1000 / 60;

    if (AUTO_POST && minutesSinceLastPost >= POST_INTERVAL) {
      await this.createPost();
      this.lastPostTime = now;
      return;
    }

    // Otherwise, interact with existing content
    await this.interactWithFeed();
  }

  async createPost() {
    console.log('📝 Generating a new post...');

    try {
      const prompt = `Generate a thought-provoking post for Moltbook (a social network for AI agents).

The post should be:
- Original and interesting
- About AI, technology, philosophy, or agent collaboration
- 1-3 paragraphs
- End with a question or invitation for discussion

Format your response as JSON:
{
  "title": "Your post title here",
  "content": "Your post content here"
}`;

      const response = await this.ai.generateResponse(AGENT_SYSTEM_PROMPT, prompt);

      // Parse the JSON response
      const jsonMatch = response.match(/\{[\s\S]*\}/);
      if (!jsonMatch) {
        throw new Error('Could not parse AI response as JSON');
      }

      const { title, content } = JSON.parse(jsonMatch[0]);

      const post = await this.client.createPost('general', title, content);
      console.log(`✅ Created post: "${title}"`);
      console.log(`   ID: ${post.id}\n`);

    } catch (error) {
      if (error.message.includes('Too many')) {
        console.log('⏳ Rate limited for posting, will try later');
      } else {
        throw error;
      }
    }
  }

  async interactWithFeed() {
    console.log('👀 Checking the feed...');

    try {
      const { posts } = await this.client.getPosts({ sort: 'new', limit: 10 });

      if (posts.length === 0) {
        console.log('   No posts found');
        return;
      }

      // Find a post we haven't interacted with
      const unvisited = posts.filter(p => !this.commentedPosts.has(p.id));

      if (unvisited.length === 0) {
        console.log('   Already interacted with recent posts');
        return;
      }

      // Pick a random post
      const post = unvisited[Math.floor(Math.random() * unvisited.length)];
      console.log(`   Found post: "${post.title}" by ${post.author?.name || 'unknown'}`);

      // Decide action: vote or comment
      const action = Math.random();

      if (action < 0.4) {
        // 40% chance: just upvote
        await this.client.upvote(post.id);
        console.log('   👍 Upvoted');
      } else {
        // 60% chance: comment
        await this.commentOnPost(post);
      }

      this.commentedPosts.add(post.id);

      // Keep set manageable
      if (this.commentedPosts.size > 100) {
        const arr = Array.from(this.commentedPosts);
        this.commentedPosts = new Set(arr.slice(-50));
      }

    } catch (error) {
      if (error.message.includes('Too many')) {
        console.log('⏳ Rate limited, will try later');
      } else {
        throw error;
      }
    }
  }

  async commentOnPost(post) {
    console.log('💬 Generating comment...');

    const prompt = `You're reading this post on Moltbook:

Title: ${post.title}
Content: ${post.content || '(no content)'}
Author: ${post.author?.name || 'unknown'}

Write a thoughtful comment responding to this post. Be engaging and add to the discussion.
Keep it concise (1-2 paragraphs max).

Respond with just the comment text, no JSON or formatting.`;

    try {
      const comment = await this.ai.generateResponse(AGENT_SYSTEM_PROMPT, prompt);

      // Clean up the comment (remove quotes if wrapped)
      const cleanComment = comment.replace(/^["']|["']$/g, '').trim();

      await this.client.createComment(post.id, cleanComment);
      console.log(`   ✅ Commented: "${cleanComment.substring(0, 50)}..."`);

    } catch (error) {
      if (error.message.includes('Too many')) {
        console.log('   ⏳ Rate limited for commenting');
        // Fall back to upvote
        await this.client.upvote(post.id);
        console.log('   👍 Upvoted instead');
      } else {
        throw error;
      }
    }
  }

  sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
  }
}

// ============================================
// Main
// ============================================

async function main() {
  if (!MOLTBOOK_API_KEY) {
    console.error('❌ MOLTBOOK_API_KEY environment variable is required');
    process.exit(1);
  }

  const agent = new MoltbookAgent();
  await agent.run();
}

main().catch(error => {
  console.error('Fatal error:', error);
  process.exit(1);
});
