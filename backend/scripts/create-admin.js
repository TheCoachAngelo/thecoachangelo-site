import 'dotenv/config';
import bcrypt from 'bcryptjs';
import readline from 'readline';
import { db } from '../src/db.js';

function ask(query, hide = false) {
  return new Promise((resolve) => {
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    if (!hide) {
      rl.question(query, (answer) => {
        rl.close();
        resolve(answer.trim());
      });
      return;
    }

    const stdin = process.stdin;
    process.stdout.write(query);
    stdin.resume();
    stdin.setRawMode?.(true);
    let data = '';
    stdin.on('data', function onData(char) {
      char = String(char);
      if (char === '\n' || char === '\r' || char === '\u0004') {
        stdin.setRawMode?.(false);
        stdin.pause();
        stdin.removeListener('data', onData);
        process.stdout.write('\n');
        rl.close();
        resolve(data.trim());
      } else if (char === '\u0003') {
        process.exit(1);
      } else if (char === '\u007f') {
        data = data.slice(0, -1);
      } else {
        data += char;
      }
    });
  });
}

const email = (process.argv[2] || await ask('Admin email: ')).toLowerCase();
const password = process.argv[3] || await ask('Admin password: ', true);

if (!email || !password) {
  console.error('Email and password are required.');
  process.exit(1);
}

const existing = db.prepare('SELECT id FROM admins WHERE email = ?').get(email);
if (existing) {
  console.error('Admin already exists with that email.');
  process.exit(1);
}

const passwordHash = bcrypt.hashSync(password, 12);
db.prepare('INSERT INTO admins (email, password_hash, role) VALUES (?, ?, ?)').run(email, passwordHash, 'editor');

console.log(`Admin created: ${email}`);
