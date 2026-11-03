"""Isolated demo. Offline by default; network use requires separate approval."""
from __future__ import annotations
import fcntl
import base64
import hashlib
import json
import os
from pathlib import Path
import urllib.request

MAX_BRIEF_BYTES = 4096
MAX_OUTPUT_TOKENS = 2048
MAX_SOURCE_BYTES = 2 * 1024 * 1024
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_IMAGE_BYTES = 8 * 1024 * 1024
MAX_REQUESTS = 4
MAX_IMAGES = 3


def bounded_text(value, label):
    if not isinstance(value, str) or not value.strip() or len(value.encode('utf-8')) > MAX_BRIEF_BYTES:
        raise ValueError(label + ' must be 1..4096 UTF-8 bytes')
    return value


MODELS = {'plan': 'muse-spark-1.3', 'image': 'muse-image-1.0'}


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def validate_plan(plan):
    if not isinstance(plan, dict):
        raise ValueError('Plan must be an object')
    concepts = plan.get('concepts', [])
    if not isinstance(concepts, list) or len(concepts) != 3:
        raise ValueError('Exactly three distinct concepts required')
    ids = [x.get('id') if isinstance(x, dict) else None for x in concepts]
    if any(not isinstance(x, str) or not x or len(x) > 80 for x in ids) or len(set(ids)) != 3:
        raise ValueError('Concept IDs must be distinct strings')
    for c in concepts:
        if not isinstance(c.get('title'), str) or not c['title'] or len(c['title']) > 160 or len(c.get('scenes', [])) != 3:
            raise ValueError('Each concept needs a title and three scenes')
        for scene in c['scenes']:
            if not isinstance(scene, dict) or not isinstance(scene.get('caption'), str) or not 0 < len(scene['caption']) <= 80:
                raise ValueError('Invalid scene caption')
            seconds = scene.get('seconds')
            if isinstance(seconds, bool) or not isinstance(seconds, (int, float)) or not 1 <= seconds <= 10:
                raise ValueError('Invalid scene duration')
    return plan


class MetaAdapter:
    """Reviewable live integration boundary. Never invoked by offline demo/tests.

    Ref: https://dev.meta.ai/docs/quickstart and /image-generation, 2026-11-03.
    A permit must name the request digest and its maximum authorized cost.
    Provider billing/credits still need checking before the permit is issued.
    """
    def __init__(self, key=None, transport=None, ledger=None):
        self.key = key or os.environ.get('MODEL_API_KEY')
        self.transport = transport
        self.ledger = Path(ledger) if ledger else Path.home() / ".local/state/viral-loop-meta-demo/live-budget.json"

    def _reserve(self, path, request_hash):
        # Reserve before I/O. Timeouts and malformed responses consume the slot.
        # No automatic reset: another process cannot silently retry or overspend.
        self.ledger.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(self.ledger, os.O_RDWR | os.O_CREAT, 0o600)
        with os.fdopen(fd, 'r+') as file:
            fcntl.flock(file, fcntl.LOCK_EX)
            raw = file.read()
            state = json.loads(raw) if raw else {'requests': []}
            rows = state['requests']
            if not isinstance(rows, list):
                raise ValueError('Invalid live budget ledger')
            images = sum(r['path'] == '/images/edits' for r in rows)
            plans = sum(r['path'] == '/responses' for r in rows)
            if (len(rows) >= MAX_REQUESTS or request_hash in [r['sha256'] for r in rows]
                    or (path == '/images/edits' and images >= MAX_IMAGES)
                    or (path == '/responses' and plans >= 1)):
                raise PermissionError('Persistent demo request budget exhausted or request already attempted')
            rows.append({'path': path, 'sha256': request_hash})
            file.seek(0)
            json.dump(state, file)
            file.truncate()
            file.flush()
            os.fsync(file.fileno())

    def _post(self, path, payload, permit):
        request_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        if not self.key or not permit or permit.get('request_sha256') != request_hash or permit.get('max_cost_usd', 0) <= 0:
            raise PermissionError('This exact live request needs separate cost approval')
        if path not in ('/responses', '/images/edits'):
            raise ValueError('Unsupported endpoint')
        if len(json.dumps(payload).encode()) > 3 * 1024 * 1024:
            raise ValueError('Request exceeds byte limit')
        if path == '/responses' and payload.get('max_output_tokens') != MAX_OUTPUT_TOKENS:
            raise ValueError('Missing output token limit')
        if path == '/images/edits' and payload.get('n') != 1:
            raise ValueError('Exactly one image per request')
        self._reserve(path, request_hash)
        if self.transport:
            result = self.transport(path, payload)
            if len(json.dumps(result).encode()) > MAX_RESPONSE_BYTES:
                raise ValueError('Response exceeds byte limit')
            return result
        request = urllib.request.Request('https://api.meta.ai/v1' + path,
            data=json.dumps(payload).encode(), method='POST',
            headers={'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json'})
        # Deliberately no retry. An uncertain result must be reviewed, not replayed.
        with urllib.request.urlopen(request, timeout=90) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ValueError('Response exceeds byte limit')
            return json.loads(raw)

    @staticmethod
    def plan_payload(brief):
        bounded_text(brief, 'Brief')
        return {'model': MODELS['plan'], 'max_output_tokens': MAX_OUTPUT_TOKENS, 'input': [{'role': 'user', 'content':
            'Return JSON with concepts: exactly 3 distinct concepts, each id, title, hook, and 3 scenes with caption and seconds. Brief: ' + brief}],
            'text': {'format': {'type': 'json_object'}}}

    def plan(self, brief, permit=None):
        data = self._post('/responses', self.plan_payload(brief), permit)
        text = ''.join(c.get('text', '') for item in data.get('output', []) for c in item.get('content', []) if c.get('type') == 'output_text')
        return validate_plan(json.loads(text))

    @staticmethod
    def image_payload(prompt, source):
        bounded_text(prompt, 'Prompt')
        with Path(source).open('rb') as file:
            source_bytes = file.read(MAX_SOURCE_BYTES + 1)
        if len(source_bytes) > MAX_SOURCE_BYTES:
            raise ValueError('Source exceeds 2 MiB')
        return {'model': MODELS['image'], 'prompt': prompt, 'n': 1,
                'images': [{'image_url': 'data:image/png;base64,' + base64.b64encode(source_bytes).decode()}],
                'size': '720x1280', 'output_format': 'png', 'response_format': 'b64_json'}

    def image(self, prompt, source, target, permit=None):
        data = self._post('/images/edits', self.image_payload(prompt, source), permit)
        blob = base64.b64decode(data['data'][0]['b64_json'], validate=True)
        if len(blob) > MAX_IMAGE_BYTES:
            raise ValueError('Image exceeds 8 MiB')
        if not blob.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('Expected PNG image, not a claimed output')
        Path(target).write_bytes(blob)
        return {'sha256': digest(target), 'model': MODELS['image'], 'synthetic': False}
