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

## Manual integration preparation (not live-verified)

`python live.py prepare-plan --brief-file brief.txt --out plan-request.json`
prepares a request and digest without a network call. The execute commands
require an exact separately approved permit. After an approved planning call,
`prepare-images` prepares three single-image requests for separate review. Each
`execute-image` sends exactly one request and saves bytes plus their hash. No
automatic retry or bulk execution is implemented. Do not publish keys, permits,
private briefs or returned data without checking their audience.

`python demo.py --plan plan.json --selected CONCEPT_ID --images images/`
can assemble verified external scene-1.png through scene-3.png. The external
image manifest records provider call count as unknown, not zero. It does not
assert that arbitrary image files were produced by Meta.

## Live request limits

Live execution is still disabled without a separately approved exact-request
permit and provider key. `max_cost_usd` records approval; it is not a provider-side
billing cap, does not prove credits exist, and never authorizes a card charge.

The adapter enforces 4096 UTF-8 bytes for each brief/prompt, 2048 maximum output
tokens for planning, a 2 MiB source image, one image per request, a 12 MiB response,
and an 8 MiB decoded image. Its persistent, file-locked ledger allows at most one
planning request and three image requests (four requests total). Reservation
happens before network I/O. Timeouts, invalid outputs and uncertain responses
consume a slot, and an identical request cannot be retried. The default ledger is
`~/.local/state/viral-loop-meta-demo/live-budget.json`; it is private local state,
not a submission artifact. Do not delete/reset or change its location to retry a
live attempt. An authorized operator must review any uncertain outcome first.

These limits bound request volume and payload size, not the dollar invoice. Live
execution, confirmed credits and any actual spending still require separate
approval. The rehearsal makes no provider calls.

## Licensing and private files

Only the isolated demo source and documentation are MIT-licensed. See
`THIRD_PARTY_NOTICES.md` for separately installed dependencies, host fonts,
trademark limits and external-image rights. No third-party assets or production
product source are relicensed. Future Meta outputs are not automatically MIT.
The loopback server serves only the UI and named preview artifacts; keys,
permits, source files and directory listings are not public endpoints.
