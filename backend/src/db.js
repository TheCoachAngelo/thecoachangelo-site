import fs from 'fs';
import path from 'path';
import Database from 'better-sqlite3';

const dbPath = process.env.DATABASE_PATH || './data/app.db';
const resolved = path.resolve(process.cwd(), dbPath);
fs.mkdirSync(path.dirname(resolved), { recursive: true });

export const db = new Database(resolved);
db.pragma('journal_mode = WAL');

db.exec(`
CREATE TABLE IF NOT EXISTS admins (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  email TEXT NOT NULL UNIQUE,
  password_hash TEXT NOT NULL,
  role TEXT NOT NULL DEFAULT 'editor',
  created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS posts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  slug TEXT NOT NULL UNIQUE,
  excerpt TEXT,
  content_html TEXT NOT NULL,
  featured_image_url TEXT,
  author_name TEXT NOT NULL DEFAULT 'Coach Angelo',
  category TEXT,
  tags TEXT,
  is_published INTEGER NOT NULL DEFAULT 0,
  published_at TEXT,
  created_at TEXT NOT NULL DEFAULT (datetime('now')),
  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_posts_slug ON posts(slug);
CREATE INDEX IF NOT EXISTS idx_posts_published ON posts(is_published, published_at);
`);

export function nowIso() {
  return new Date().toISOString();
}
