# Hogwarts dependencies

## keepstream

Desk Session client (TCP VIDEO + INPUT) and optional H.264→RGB decode.

| Remote | URL |
|--------|-----|
| GitHub | https://github.com/digitizable/keepstream |
| Gitea | `git@gitea.anguish.sh:anguish/keepstream.git` |

**Vendored as git submodule:** `third_party/keepstream`  
Reach plugin entry (`ui.py`) adds `third_party/keepstream/src` to `sys.path`.

```bash
# clone hogwarts with submodules
git clone --recurse-submodules git@github.com:digitizable/hogwarts.git

# or after clone
git submodule update --init --recursive

# optional editable install into the Reach venv
pip install -e third_party/keepstream
```

Imports:

```python
from keepstream import KeepstreamClient
from keepstream.h264dec import ensure_gst_init, decode_h264_au_to_rgb
# still works:
from hogwarts.keepstream import KeepstreamClient
from hogwarts.h264dec import ensure_gst_init
```

The **agent/server** Keepstream face still lives in `agent/agent.py` (lab implant).
