# AGENTS.md — game-factory

Rules for agents working in this repository. Each rule says what went wrong without it.
Background is in `docs/`; keep this file to rules.

## Data

- Never commit a full package, a project snapshot, `git.log` with asset diffs, or package zips here; only
  tools and docs. _(failure: a package is tens of GB, far past GitHub's 100 MB file limit)_
- Keep this repository private. _(failure: the docs describe a private repository and its asset data)_
- Step reasons are the builder's own narration or notes, or the commit message; never write them with a
  model. _(failure: reasons written after the fact make a package a reconstruction rather
  than a record)_
- Anonymize authors as `dev_NN` and run the leak scan (real names, e-mails, `C:\Users\…`, `/Users/…`, `/home/…`)
  over every text file of a package before calling it done. _(failure: commit metadata and asset files can
  carry real names and machine paths)_
