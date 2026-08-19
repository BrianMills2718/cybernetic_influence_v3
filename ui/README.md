# User interfaces

Canonical inventory: `registry.yaml` -- two real surfaces: the local
operator/review app (`frontend/src` -> built into `web/`, served by
`make serve`) and the separately-deployed public Waltzman demo
(`public/waltzman/`). Read it before adding, changing, or replacing any UI.
This file is the required concern front door; `registry.yaml` is where the
actual inventory lives and is kept current.
