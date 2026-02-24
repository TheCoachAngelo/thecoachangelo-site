# The Coach Angelo Backend (Custom Option B)

Custom backend for blog publishing and future admin features.

## Stack
- Node.js + Express
- SQLite (`better-sqlite3`)
- JWT auth for admin API

## Features (v1)
- Admin login
- Blog post CRUD (create/update/delete/list)
- Public posts API
- Ready to power `blog.html` on the main site

## Quick Start
1. `cd backend`
2. `cp .env.example .env`
3. `npm install`
4. `npm run create-admin`
5. `npm run dev`

Backend runs on `http://localhost:4000` by default.

## API (v1)
- `GET /api/health`
- `GET /api/posts`
- `GET /api/posts/:slug`
- `POST /api/admin/login`
- `GET /api/admin/me` (Bearer token)
- `GET /api/admin/posts` (Bearer token)
- `POST /api/admin/posts` (Bearer token)
- `PUT /api/admin/posts/:id` (Bearer token)
- `DELETE /api/admin/posts/:id` (Bearer token)

## Example Admin Post Payload
```json
{
  "title": "How to structure a fat loss phase",
  "slug": "fat-loss-phase-structure",
  "excerpt": "The framework I use for clients.",
  "content_html": "<p>Article HTML here...</p>",
  "featured_image_url": "https://...",
  "category": "Fat Loss",
  "tags": ["fat loss", "nutrition"],
  "is_published": true
}
```

## Deployment Notes
- For production, move from SQLite to Postgres later if needed.
- Deploy backend separately (VPS / Railway / Render).
- Keep your current frontend on `thecoachangelo.com` and call this API.

## Admin UI
- Open `http://localhost:4000/admin`
- Login with the account created using `npm run create-admin`
- Create/edit/publish posts in the browser
