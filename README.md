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

Run `python demo.py`, then `python server.py` in this directory.
Run tests with `python -m unittest discover -s tests`.

The planned submission needs a 3-minute demo video and public source. This
prototype is not a submitted entry. Only this isolated demo source is public;
the production Viral Loop repository remains private.

## Implemented and remaining

- Implemented: editable brief with synthetic template directions, exactly three fixture concepts,
  direction selection, rights review, local assembly for any selected direction,
  media hashes and tested provider request contracts.
- Not implemented in the UI: real Meta planning and real Meta image generation.
  The fixed coffee illustration does not adapt semantically to the input brief.
- Not verified: live Meta responses, credits, final 3-minute demo or submission.
  The API adapter is a reviewed boundary, not evidence of successful integration.

The local server binds only 127.0.0.1:8765 and rejects cross-origin POSTs.
It has no API-key entry or live-provider execution endpoint.

## Live adapter safety boundary

The request digest permit is an application preflight gate, not a provider billing
hard cap. `max_cost_usd` records the separately approved budget; it does not stop
provider billing at that amount. Verify current prices, remaining credits and
account billing before any live request. This rehearsal server never invokes
the adapter. Failed or uncertain live calls must not be automatically replayed.
