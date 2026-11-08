---
id: K-0081
kind: test-procedure
title: Running Qt-importing tests in a cloud session: tools/cloud_tests.py
status: confirmed
by: claude
created: 2026-11-08T00:38:51+00:00
concerns: tools/cloud_tests.py, tests/test_parity.py, tests/test_glasses.py
from: dec:DEC-0125
---
Cloud sessions have no PySide6, pyserial, fastapi, libzim or mutagen, so about 80 tests fail on import, among them the ones that matter most for new voice tools: test_parity and test_glasses' 'every ask reaches its app's own tools' (both build the desktop registry through core/application.py). tools/cloud_tests.py puts a stand-in module (MagicMock attributes, any submodule) in place of each missing library and runs pytest. With it those checks pass here; what still fails is the endpoint tests (FastAPI can't be faked) and music playback, which are the library's absence, not the code. Used on 2026-11-07 to confirm the night's new voice tools didn't steal any glasses ask.
