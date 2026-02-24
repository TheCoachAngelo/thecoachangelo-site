import { Router } from 'express';
import bcrypt from 'bcryptjs';
import { db, nowIso } from '../db.js';
import { signAdminToken } from '../auth.js';
import { requireAuth } from '../middleware/requireAuth.js';
import slugify from 'slugify';

const router = Router();

function normalizePostInput(body) {
  const title = String(body.title || '').trim();
  const slugInput = String(body.slug || '').trim();
  const slug = slugify(slugInput || title, { lower: true, strict: true });
  const excerpt = String(body.excerpt || '').trim();
  const contentHtml = String(body.content_html || body.contentHtml || '').trim();
  const featuredImageUrl = String(body.featured_image_url || body.featuredImageUrl || '').trim();
  const authorName = String(body.author_name || body.authorName || 'Coach Angelo').trim();
  const category = String(body.category || '').trim();
  const tags = Array.isArray(body.tags) ? body.tags.join(',') : String(body.tags || '').trim();
  const isPublished = body.is_published || body.isPublished ? 1 : 0;

  if (!title) throw new Error('Title is required');
  if (!slug) throw new Error('Slug is required');
  if (!contentHtml) throw new Error('content_html is required');

  return { title, slug, excerpt, contentHtml, featuredImageUrl, authorName, category, tags, isPublished };
}

router.post('/login', (req, res) => {
  const email = String(req.body.email || '').trim().toLowerCase();
  const password = String(req.body.password || '');

  if (!email || !password) {
    return res.status(400).json({ error: 'Email and password are required' });
  }

  const admin = db.prepare('SELECT * FROM admins WHERE email = ?').get(email);
  if (!admin) return res.status(401).json({ error: 'Invalid credentials' });

  const ok = bcrypt.compareSync(password, admin.password_hash);
  if (!ok) return res.status(401).json({ error: 'Invalid credentials' });

  const token = signAdminToken(admin);
  res.json({ token, admin: { id: admin.id, email: admin.email, role: admin.role } });
});

router.get('/me', requireAuth, (req, res) => {
  res.json({ user: req.user });
});

router.get('/posts', requireAuth, (_req, res) => {
  const posts = db.prepare('SELECT * FROM posts ORDER BY datetime(created_at) DESC').all();
  res.json({ posts: posts.map(mapPost) });
});

router.post('/posts', requireAuth, (req, res) => {
  try {
    const input = normalizePostInput(req.body);
    const now = nowIso();
    const publishedAt = input.isPublished ? (req.body.published_at || req.body.publishedAt || now) : null;

    const stmt = db.prepare(`
      INSERT INTO posts (title, slug, excerpt, content_html, featured_image_url, author_name, category, tags, is_published, published_at, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);
    const result = stmt.run(
      input.title,
      input.slug,
      input.excerpt,
      input.contentHtml,
      input.featuredImageUrl,
      input.authorName,
      input.category,
      input.tags,
      input.isPublished,
      publishedAt,
      now,
      now
    );

    const post = db.prepare('SELECT * FROM posts WHERE id = ?').get(result.lastInsertRowid);
    res.status(201).json({ post: mapPost(post) });
  } catch (err) {
    if (String(err.message).includes('UNIQUE')) {
      return res.status(409).json({ error: 'Slug already exists' });
    }
    res.status(400).json({ error: err.message || 'Invalid request' });
  }
});

router.put('/posts/:id', requireAuth, (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) return res.status(400).json({ error: 'Invalid id' });

  const existing = db.prepare('SELECT * FROM posts WHERE id = ?').get(id);
  if (!existing) return res.status(404).json({ error: 'Post not found' });

  try {
    const input = normalizePostInput({ ...existing, ...req.body });
    const now = nowIso();
    const publishedAt = input.isPublished
      ? (req.body.published_at || req.body.publishedAt || existing.published_at || now)
      : null;

    db.prepare(`
      UPDATE posts
      SET title = ?, slug = ?, excerpt = ?, content_html = ?, featured_image_url = ?, author_name = ?,
          category = ?, tags = ?, is_published = ?, published_at = ?, updated_at = ?
      WHERE id = ?
    `).run(
      input.title,
      input.slug,
      input.excerpt,
      input.contentHtml,
      input.featuredImageUrl,
      input.authorName,
      input.category,
      input.tags,
      input.isPublished,
      publishedAt,
      now,
      id
    );

    const post = db.prepare('SELECT * FROM posts WHERE id = ?').get(id);
    res.json({ post: mapPost(post) });
  } catch (err) {
    if (String(err.message).includes('UNIQUE')) {
      return res.status(409).json({ error: 'Slug already exists' });
    }
    res.status(400).json({ error: err.message || 'Invalid request' });
  }
});

router.delete('/posts/:id', requireAuth, (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) return res.status(400).json({ error: 'Invalid id' });

  const result = db.prepare('DELETE FROM posts WHERE id = ?').run(id);
  if (!result.changes) return res.status(404).json({ error: 'Post not found' });
  res.status(204).send();
});

function mapPost(row) {
  if (!row) return null;
  return {
    id: row.id,
    title: row.title,
    slug: row.slug,
    excerpt: row.excerpt,
    content_html: row.content_html,
    featured_image_url: row.featured_image_url,
    author_name: row.author_name,
    category: row.category,
    tags: row.tags ? row.tags.split(',').map((t) => t.trim()).filter(Boolean) : [],
    is_published: !!row.is_published,
    published_at: row.published_at,
    created_at: row.created_at,
    updated_at: row.updated_at
  };
}

export default router;
