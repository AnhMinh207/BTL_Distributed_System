import hashlib
import hmac
import os
import re
import sqlite3

from .common import Service, Problem, text_field, require, uid, encode_token


class Identity(Service):
    def __init__(self):
        super().__init__('identity')
        self.db.schema('''CREATE TABLE IF NOT EXISTS users(
            id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, role TEXT NOT NULL,
            salt TEXT NOT NULL, password_hash TEXT NOT NULL);''')

    def dispatch(self, method, path, body, headers, corr):
        require(method == 'POST' and path in ('/register', '/login'), 404, 'Route not found')
        username = text_field(body, 'username', 3, 64).lower()
        require(re.fullmatch(r'[a-z0-9_.-]+', username), 400, 'Invalid username')
        password = text_field(body, 'password', 10, 128)
        if path == '/register':
            role = body.get('role')
            require(role in ('passenger', 'driver'), 400, 'Invalid role')
            salt = os.urandom(16).hex()
            hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), bytes.fromhex(salt), 200000).hex()
            user = dict(id=uid(), username=username, role=role)
            try:
                with self.db.tx() as db:
                    db.execute('INSERT INTO users VALUES(?,?,?,?,?)',
                               (user['id'], username, role, salt, hashed))
            except sqlite3.IntegrityError:
                raise Problem(409, 'Username already exists')
            return {**user, 'token': encode_token(user)}
        with self.db.connect() as db:
            row = db.execute('SELECT * FROM users WHERE username=?', (username,)).fetchone()
        salt = bytes.fromhex(row['salt']) if row else bytes(16)
        hashed = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, 200000).hex()
        require(row is not None and hmac.compare_digest(hashed, row['password_hash']), 401, 'Invalid credentials')
        user = {key: row[key] for key in ('id', 'username', 'role')}
        return {**user, 'token': encode_token(user)}
