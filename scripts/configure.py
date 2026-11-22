"""Create local secrets once; never echo them or overwrite an existing .env."""
import secrets
from pathlib import Path

root = Path(__file__).resolve().parents[1]
target = root / '.env'
if target.exists():
    print('.env already exists; kept existing configuration.')
else:
    value = (root / '.env.example').read_text(encoding='utf-8')
    value = value.replace('AUTH_SECRET=\n', 'AUTH_SECRET=' + secrets.token_hex(32) + '\n')
    value = value.replace('SERVICE_KEY=\n', 'SERVICE_KEY=' + secrets.token_hex(32) + '\n')
    target.write_text(value, encoding='utf-8')
    print('Created .env with random secrets. Keep this file private.')
