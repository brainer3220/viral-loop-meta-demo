# Viral Loop: Meta content studio demo

Hackathon prototype, separate from the production app. No production auth, billing,
storage, deployment settings or user data is included in this directory.

The default demo is offline and every image and plan is synthetic. It is not
proof of Meta API integration. Live execution is disabled unless the account
owner separately approves cost and rights. No automatic paid retries.

Sources checked 2026-11-03:
- https://dev.meta.ai/docs/quickstart
- https://dev.meta.ai/docs/models
- https://dev.meta.ai/docs/image-generation

Requires Python 3.10+, Pillow (`pip install -r requirements.txt`), FFmpeg and FFprobe.

Run `python demo.py`, then `python -m http.server 8765` in this directory.
Run tests with `python -m unittest discover -s tests`.

The planned submission needs a 3-minute demo video and public source. This
prototype is not a submitted entry. Only this isolated demo source is public;
the production Viral Loop repository remains private.
