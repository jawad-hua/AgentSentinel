# Phase 2 incremental patch manifest

Apply inside D:\AgentSentinel after stopping both AgentSentinel processes.
No files are deleted. Existing .env, .env.local, databases and dependency lockfiles are excluded.
The single n8n master has note-only changes; no re-import is required.

| Change | Project-relative path | SHA-256 |
| --- | --- | --- |
| MODIFIED FILE | `AGENTS.md` | `43f7eb3cd2f8b2af3e821377d08a4dea6b96b6647655c508f31f0c3221129530` |
| MODIFIED FILE | `README.md` | `2575ac087ac258937475f496341e0a141221f8fb4b8c1f27c3445a817f479890` |
| MODIFIED FILE | `backend/app/config.py` | `01138be4233143eb530e7d633375614e7df7a59a68c97866cf72b4517ca4288b` |
| MODIFIED FILE | `backend/app/integrations/n8n.py` | `33cc9323aa328617ddffcac0ed6e5a8b411263eee02adef2f2b1a4baa07c8f02` |
| MODIFIED FILE | `backend/app/main.py` | `5050174a94d70dfe3b2f40935f4a858d1faf11191b493a0185d174a6347f1a7e` |
| NEW FILE | `backend/app/monitoring/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| NEW FILE | `backend/app/monitoring/models.py` | `434c3cbcf2bdb7ea8bdfa94c07d15ca6f8bb717d8fce70af4d7458db7bfc0774` |
| NEW FILE | `backend/app/monitoring/normalize.py` | `9a7fb5662899f93d84694fda32ea4149b6f9c1ea3c4753231d88c382656ed837` |
| NEW FILE | `backend/app/monitoring/routes.py` | `373321b85bb1e9daa0895fce20775869bbd95574317d46ab8d013b3f948905dc` |
| NEW FILE | `backend/app/monitoring/service.py` | `9a16c8b7ecf531fae201865444f8863f64aa1a154978152ecb18e916f33f94c1` |
| MODIFIED FILE | `backend/migrations/env.py` | `9e22beba86482ab70752f26e4c73a762bb72e4a7ed5777e00a166fa9eb8a43b0` |
| NEW FILE | `backend/migrations/versions/0002_monitoring.py` | `7ddc7d4de144caa25b97184ae15fd9f2b92d6eaa859bc6cba6d52c7be63f54db` |
| MODIFIED FILE | `backend/pyproject.toml` | `013a3a721463f421d6788c01f8058c5c2bf6e4f54534d7628a5332e8fbe9a25c` |
| NEW FILE | `backend/tests/__init__.py` | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| MODIFIED FILE | `backend/tests/test_foundation.py` | `5bfce509fc1f037d8abd178e2d53e65c00f5caecd3525b7aefa92b6f82013fb5` |
| NEW FILE | `backend/tests/test_live_n8n.py` | `b321ca3331b0b1f8dcc2b9fb4fea2c73999cd1b5b76b4703f12d5e812e040140` |
| NEW FILE | `backend/tests/test_monitoring.py` | `d1bc51710ed3643c76fbec0d3dee0160eaf691ed4f7cc248eb4eb78bf9483ee8` |
| MODIFIED FILE | `docs/ARCHITECTURE.md` | `fd372ff33d4b1b5f08e4b54507d270fa5185b18c4fedd7fe48e9411f0d6f56e9` |
| NEW FILE | `docs/MONITORING.md` | `fcfd6268e19a85f27194983fee3b40ce6a590a51e0d3bba1dee10ee1a5e144fe` |
| NEW FILE | `docs/PHASE_2_SETUP.md` | `dae095b722d2b737854350fdf93df07a7bd15569919bb5de717f984cce695ddf` |
| NEW FILE | `docs/PHASE_2_VERIFICATION.md` | `3fe3c8af43c9be7a2b188e7eff18edaa1660cbe1078dbf24153c3a183de3c423` |
| MODIFIED FILE | `docs/VERIFICATION.md` | `a089b938fcf9931ac088dfcee78324519c528fd4cc8287fd6add413a6ec7d3e5` |
| NEW FILE | `frontend/src/app/api/events/route.ts` | `c4c6c35f0398b25fb35471ca81a3dc21b40beeacaae191ae7af4e423d52f5161` |
| NEW FILE | `frontend/src/app/api/monitor/actions/route.ts` | `e6cd7050407afd86dedd2397e4c36a04dd4f3bd03c16c403ea9305974c25f129` |
| MODIFIED FILE | `frontend/src/app/globals.css` | `7b111594d46cef92933250b8d3052d016e141c2a801c2265788fd9deb5e4fb67` |
| NEW FILE | `frontend/src/app/incidents/[id]/page.tsx` | `87165686c1f2ff00367dfaa155a332ee9d7ffd15116709f6d74f6334ede8b6bc` |
| NEW FILE | `frontend/src/app/incidents/page.tsx` | `180c0050dd45e77ebaee0214ce7aa96b5704da6e72a5247e5d4d3bb9207663c7` |
| MODIFIED FILE | `frontend/src/app/page.tsx` | `9eaf063f76e1ba6cc99b92ac2741078888b2d2dabe1858c51641ef15698bcc5f` |
| NEW FILE | `frontend/src/components/live-updates.tsx` | `a3a1aa3dbcebd950678361c49baa8392cdec8ce0ede21c9ba55db0538a70b4d9` |
| NEW FILE | `frontend/src/components/monitoring-panel.tsx` | `6e8aa825f3746d83341718c3c926f890440283ab0fbc02f931e28cdba9353443` |
| MODIFIED FILE | `frontend/src/lib/api.ts` | `c80d221e5194be9c2dc510572593890ea092c9cdd580b75ae3d24f72a2387638` |
| NEW FILE | `frontend/src/lib/monitoring.ts` | `af1c3c32e63ffcddb4692e2f95acd935d6da06baeed8a5b7739b12d3986096e9` |
| NEW FILE | `frontend/src/lib/origin.ts` | `774d1bde9476c12a69438f2ccbb37d76fdef9a8f0df6d6d084ace54fbc397412` |
| MODIFIED FILE | `n8n/AgentSentinel_Master.json` | `e552140baa0a6fa2a83ad71a065a979d71467b9719adb0fe059eda050b9ddee8` |
| NEW FILE | `docs/PHASE_2_MANIFEST.md` | Self manifest |

DELETED FILE: none.
