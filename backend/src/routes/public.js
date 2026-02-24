import { Router } from 'express';
import { db } from '../db.js';

const router = Router();

router.get('/health', (_req, res) => {
  res.json({ ok: true, service: 'thecoachangelo-backend' });
});

router.get('/posts', (req, res) => {
  const limit = Math.min(Number(req.query.limit) || 20, 100);
  const posts = db.prepare(`
    SELECT id, title, slug, excerpt, featured_image_url, author_name, category, tags, published_at, created_at, updated_at
    FROM posts
    WHERE is_published = 1
    ORDER BY datetime(COALESCE(published_at, created_at)) DESC
    LIMIT ?
  `).all(limit);

  res.json({ posts: posts.map(mapSummary) });
});

router.get('/posts/:slug', (req, res) => {
  const post = db.prepare(`
    SELECT * FROM posts
    WHERE slug = ? AND is_published = 1
    LIMIT 1
  `).get(req.params.slug);

  if (!post) return res.status(404).json({ error: 'Post not found' });
  res.json({ post: mapFull(post) });
});

function mapSummary(row) {
  return {
    id: row.id,
    title: row.title,
    slug: row.slug,
    excerpt: row.excerpt,
    featured_image_url: row.featured_image_url,
    author_name: row.author_name,
    category: row.category,
    tags: row.tags ? row.tags.split(',').map((t) => t.trim()).filter(Boolean) : [],
    published_at: row.published_at,
    created_at: row.created_at,
    updated_at: row.updated_at
  };
}

function mapFull(row) {
  return { ...mapSummary(row), content_html: row.content_html };
}

export default router;
