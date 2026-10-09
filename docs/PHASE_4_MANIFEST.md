# Phase 4 incremental patch manifest

Apply over Phase 3 with its rate-limit hotfix. No deleted files.
No environment files, database, operational seeds or installed dependencies are shipped.

| Change | Exact project-relative path | SHA-256 |
| --- | --- | --- |
| MODIFIED FILE | `AGENTS.md` | `c07b5c2b93a0e91381b978749d33f30e05d4f95638f6580c362ac1b625b458c0` |
| MODIFIED FILE | `README.md` | `772ce0dea94f5155e666c7aa88a5e252bfc9a0039747bafbdd2c21e462d1a981` |
| MODIFIED FILE | `backend/.env.example` | `d138b3a8da101d7f972d7d0fae625ab0f08e06e9ca91f67dfe4a13b472a8ac23` |
| MODIFIED FILE | `backend/app/config.py` | `d14b1f3bc3bd162432e9265c808dd2f7fd147083faf439587c2755e55924dfee` |
| MODIFIED FILE | `backend/app/integrations/n8n.py` | `1d7ba33fd0ed2fb7bd3dbd2ba88f370d19193970b0521eb4ede3cbb7c590c46c` |
| MODIFIED FILE | `backend/app/investigation/evidence.py` | `5962163512e3b95cbf55c386b214de98dc3f7b9c0218aba4758c1513139bf2da` |
| MODIFIED FILE | `backend/app/investigation/service.py` | `116e4594580b41ea896eb69e24e4fcb5272936f81a46a68b4449d4e29656c959` |
| MODIFIED FILE | `backend/app/main.py` | `101c86289574ce13ad98bcdb087bfe4375d1e8001d3742d97e33db5e7a47295c` |
| MODIFIED FILE | `backend/app/monitoring/service.py` | `f01890c5233ebe2f8bca2a1bf560ca314ce46edaf101ce38cfe8afcbd6afbcb9` |
| NEW FILE | `backend/app/repairs/__init__.py` | `01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b` |
| NEW FILE | `backend/app/repairs/approval.py` | `db2ac150261bb9834d1572ab47c983c7535b63a7dd06d0a0ae259366cdb5ec87` |
| NEW FILE | `backend/app/repairs/models.py` | `a0e2ac78f9637f2f05074f149d7b3ca127534ad95dd3e089675235d9100e3e82` |
| NEW FILE | `backend/app/repairs/patches.py` | `7b7c20dfdf9e351c5273db9d683c23514dccb39e403e4a1fe7164f3f68549c79` |
| NEW FILE | `backend/app/repairs/routes.py` | `c09c2a3f1281e72d2017cb6bf9d11ea047efab72d3e9f643e62cf70ecfc7126a` |
| NEW FILE | `backend/app/repairs/service.py` | `67fd09d0f285ded47ee631eccf09dc2e42e1dd1b9fa6f46694f92f3a4b6260b2` |
| NEW FILE | `backend/app/repairs/verification.py` | `03f7488b0482a462f8ff7ce8c002f3a141948897f59e08ccdcbd4ef0b5133fdd` |
| MODIFIED FILE | `backend/migrations/env.py` | `65484ec3718062b05c0b66d75d6de2444e5e87290f38d6b48aa4495688b98872` |
| NEW FILE | `backend/migrations/versions/0004_repairs.py` | `dd4ee60730b9e92aa3b9db61fd866ef62a3bf23c01a037b8abeb284a3d541d5d` |
| MODIFIED FILE | `backend/pyproject.toml` | `b61b156b6a6082350b91f5e2623de0c59fd6a90f6c1005ef1a14c00b755dc5c2` |
| MODIFIED FILE | `backend/requirements-lock.txt` | `aebe4b5806cc13da13b0cf3b6541683be84f07bfa024896dd7b10664760d8a25` |
| NEW FILE | `backend/tests/test_repairs.py` | `d74a033179519dfeaed61bb1ce404cbb0eadcb9fcb76baad125b59de636ab191` |
| MODIFIED FILE | `docs/ARCHITECTURE.md` | `5372cdc7f8fbddd2b8950eb43e5cbe28eeb0a5c61fd5305b4e5e0ba0da411026` |
| MODIFIED FILE | `docs/INVESTIGATION.md` | `bbb7ff2e69a36bbcd19b609ed8995960f8e35b6df85e62cf7544cd86fd963569` |
| MODIFIED FILE | `docs/PHASE_3_RATE_LIMIT_FIX.md` | `f1a4f18dbc9df5cc520c52d924239609d778ac090be75b7fee14c6ea38ddac83` |
| NEW FILE | `docs/PHASE_4_SETUP.md` | `4cf58634412587ffd33f7efe522d01052a9aa603bffc67231507784a05496f29` |
| NEW FILE | `docs/PHASE_4_VERIFICATION.md` | `0ae1df6d68566c9520cc8cad0bbbdd50394f64b225b0b5b6605cd0911f86b9ba` |
| NEW FILE | `docs/REPAIRS.md` | `4f6cb864dbc2e6534a8c8ff4b4702a953d48cad4167bd31c09d036926c55dae6` |
| MODIFIED FILE | `docs/SECURITY.md` | `e09ee44dfbb8ec81eb1cd4de1213287a718f0f53e143e13ecae9b996ade3fb21` |
| NEW FILE | `frontend/src/app/api/repairs/route.ts` | `0c99bda591f9a3ab5c6bf268d6ee9f3735dd01456d3082be1370838f49262394` |
| MODIFIED FILE | `frontend/src/app/globals.css` | `17188e14df4b3f142020c979f622b84e6ae90211bbb7bce55169281db6a5247f` |
| MODIFIED FILE | `frontend/src/app/incidents/[id]/page.tsx` | `f103c746b5ff49bb8856ba4e86c7acf97b626034103ddcbf9ef601d4cef4d415` |
| MODIFIED FILE | `frontend/src/components/investigation-panel.tsx` | `bd124e8d4b13458faafe7c91ad7f9aa6eabcc46813b6107b8946911e1091c05d` |
| NEW FILE | `frontend/src/components/repair-controls.tsx` | `e13a20eaf3be4f8a12a66b95dc4971a0846a9857093f12dd36fa78528c7d2e5a` |
| NEW FILE | `frontend/src/components/repair-panel.tsx` | `ea87f6d6c839cfba8f8c324ef12db4a2e97bcf651d32579d062f86f3e6159696` |
| NEW FILE | `frontend/src/lib/repairs.ts` | `4e145bcd4f16ed6ab8542ae392f5f358a058820daac67c1bd0195ace13085ef2` |
| MODIFIED FILE | `n8n/AgentSentinel_Master.json` | `db8cbdee9051dadf630eb9402c6e77ba3f53c3a1cf95eebc3d6d8fec723c53c9` |
| NEW FILE | `scripts/setup_repairs.py` | `24fa21bd6da7fa599a62cab96eb065ba38e120e7f6d8a3e48c1d3feb43f7383e` |
| NEW FILE | `docs/PHASE_4_MANIFEST.md` | Self |
