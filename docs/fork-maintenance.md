# Maintaining the SignalForge nsemine fork

This repository is a maintained fork of
[**kbizme/nsemine**](https://github.com/kbizme/nsemine), distributed under its
existing MIT licence and retaining upstream history. The GitHub repository is
named `signalforge-nsemine`; the Python distribution/import remains `nsemine`.

## Branch model
- `main`: reviewed and tested release baseline.
- `develop`: integration branch; normal PR target.
- `fix/*`, `feature/*`, `chore/*`: focused working branches from `develop`.

Track cross-repository work in
[SignalForge GitHub issues](https://github.com/harishkamathuk/signalforge/issues).
Fork PRs link the authoritative issue; no duplicate issue is necessary.

## Local Python 3.12 development

```powershell
git clone https://github.com/harishkamathuk/signalforge-nsemine.git
cd signalforge-nsemine
git switch develop
git remote add upstream https://github.com/kbizme/nsemine.git
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python -m unittest discover -s tests -p "test_*.py" -v
```

If the checkout has no tests yet, the test command alone does not prove success:
CI includes a separate installation/import smoke test. Do not run live NSE requests
as an unlabelled part of the offline suite.

## Upstream synchronisation
Inspect upstream changes before adopting them. The triple-dot diff below shows changes on upstream since the common ancestor; it is **not** a complete comparison of the fork and upstream branch tips.

```bash
git fetch upstream
git log --oneline develop..upstream/main
git diff develop...upstream/main  # incoming upstream changes since merge base
git log --oneline upstream/main..develop  # commits unique to the fork
git diff upstream/main..develop  # full differences between both branch tips
```

Integrate approved changes through a review branch/PR into `develop`.
Resolve any conflicts with fork-specific transport and data semantics deliberately,
then rerun the full relevant regression suite. Do not auto-sync unreviewed changes.

## Releases and SignalForge consumption
Tag commits only after recorded tests and any required live acquisition checks.
Install SignalForge's dependency from a **tested exact commit SHA** rather than
the moving `develop` branch, e.g.:

```bash
python -m pip install "nsemine @ git+https://github.com/harishkamathuk/signalforge-nsemine.git@<tested-commit-sha>"
```

The `requirements.txt` file is an upstream pinned environment snapshot; runtime
dependency declarations are in `pyproject.toml`. Reconcile and test them
explicitly before treating either as a release lockfile. Do not publish fork
artifacts under the upstream maintainer's identity.
