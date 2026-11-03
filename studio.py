"""Isolated demo. Offline by default; network use requires separate approval."""
from __future__ import annotations
import base64
import hashlib
import json
import os
from pathlib import Path
import urllib.request

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
    def __init__(self, key=None, transport=None):
        self.key = key or os.environ.get('MODEL_API_KEY')
        self.transport = transport

    def _post(self, path, payload, permit):
        request_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
        if not self.key or not permit or permit.get('request_sha256') != request_hash or permit.get('max_cost_usd', 0) <= 0:
            raise PermissionError('This exact live request needs separate cost approval')
        if self.transport:
            return self.transport(path, payload)
        request = urllib.request.Request('https://api.meta.ai/v1' + path,
            data=json.dumps(payload).encode(), method='POST',
            headers={'Authorization': 'Bearer ' + self.key, 'Content-Type': 'application/json'})
        # Deliberately no retry. An uncertain result must be reviewed, not replayed.
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.load(response)

    @staticmethod
    def plan_payload(brief):
        return {'model': MODELS['plan'], 'input': [{'role': 'user', 'content':
            'Return JSON with concepts: exactly 3 distinct concepts, each id, title, hook, and 3 scenes with caption and seconds. Brief: ' + brief}],
            'text': {'format': {'type': 'json_object'}}}

    def plan(self, brief, permit=None):
        data = self._post('/responses', self.plan_payload(brief), permit)
        text = ''.join(c.get('text', '') for item in data.get('output', []) for c in item.get('content', []) if c.get('type') == 'output_text')
        return validate_plan(json.loads(text))

    @staticmethod
    def image_payload(prompt, source):
        return {'model': MODELS['image'], 'prompt': prompt, 'n': 1,
                'images': [{'image_url': 'data:image/png;base64,' + base64.b64encode(Path(source).read_bytes()).decode()}],
                'size': '720x1280', 'output_format': 'png', 'response_format': 'b64_json'}

    def image(self, prompt, source, target, permit=None):
        data = self._post('/images/edits', self.image_payload(prompt, source), permit)
        blob = base64.b64decode(data['data'][0]['b64_json'], validate=True)
        if not blob.startswith(b'\x89PNG\r\n\x1a\n'):
            raise ValueError('Expected PNG image, not a claimed output')
        Path(target).write_bytes(blob)
        return {'sha256': digest(target), 'model': MODELS['image'], 'synthetic': False}
