import 'dotenv/config';
import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import publicRoutes from './routes/public.js';
import adminRoutes from './routes/admin.js';
import './db.js';

const app = express();
const port = Number(process.env.PORT || 4000);

const allowedOrigins = [
  process.env.ADMIN_ORIGIN,
  process.env.PUBLIC_SITE_ORIGIN,
  'http://localhost:3000',
  'http://127.0.0.1:3000',
  'http://localhost:5500',
  'http://127.0.0.1:5500'
].filter(Boolean);

app.use(helmet({ crossOriginResourcePolicy: false }));
app.use(cors({
  origin(origin, cb) {
    if (!origin) return cb(null, true);
    if (allowedOrigins.includes(origin)) return cb(null, true);
    return cb(new Error(`Origin not allowed: ${origin}`));
  }
}));
app.use(express.json({ limit: '2mb' }));
app.use(morgan('dev'));

app.get('/', (_req, res) => {
  res.json({ ok: true, message: 'The Coach Angelo backend is running' });
});

app.use('/api', publicRoutes);
app.use('/api/admin', adminRoutes);

app.use((err, _req, res, _next) => {
  console.error(err);
  const status = err.status || 500;
  res.status(status).json({ error: status === 500 ? 'Internal server error' : err.message });
});

app.listen(port, () => {
  console.log(`Backend running on http://localhost:${port}`);
});
