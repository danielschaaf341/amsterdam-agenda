"""Evaluate a Nuxt 2 `window.__NUXT__=(function(a,b,...){...})(...)` payload into plain JSON.

The payload is a self-contained JS expression, so we run it in Node's `vm` sandbox (no network, no DOM)
and print JSON. Used by sites built by the agency cre8ion (Rialto, ITA).
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess

_NODE_PROG = r"""
const vm = require('vm');
let src = '';
process.stdin.on('data', c => src += c);
process.stdin.on('end', () => {
  const sandbox = { window: {} };
  vm.runInNewContext(src, sandbox, { timeout: 5000 });
  process.stdout.write(JSON.stringify(sandbox.window.__NUXT__));
});
"""


def eval_nuxt(html: str) -> dict:
    m = re.search(r"<script>\s*(window\.__NUXT__\s*=.*?)</script>", html, re.S)
    if not m:
        raise ValueError("no window.__NUXT__ payload in page")
    node = shutil.which("node")
    if not node:
        raise RuntimeError("node is required to read Nuxt payloads")
    res = subprocess.run([node, "-e", _NODE_PROG], input=m.group(1), capture_output=True, text=True, timeout=30)
    if res.returncode != 0:
        raise RuntimeError(f"node failed: {res.stderr[:300]}")
    return json.loads(res.stdout)
