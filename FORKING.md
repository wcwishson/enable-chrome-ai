# Fork Setup And Upstream Sync

Use this flow if you publish your own fork while tracking upstream changes.

## 1. Configure remotes

In your forked local clone:

```bash
git remote set-url origin <your-fork-url>
git remote add upstream https://github.com/lcandy2/enable-chrome-ai.git
```

Verify:

```bash
git remote -v
```

`origin` should be your fork. `upstream` should be the original project.

## 2. Keep your fork updated

```bash
git fetch upstream
git rebase upstream/main
git push origin main
```

If your fork uses merge instead of rebase:

```bash
git fetch upstream
git merge upstream/main
git push origin main
```

## 3. Rebuild the portable app after URL/remotes change

The `.app` embeds upstream as its default update source.  
If your repo has an `upstream` remote, that URL is embedded. Otherwise it falls back to:
`https://github.com/lcandy2/enable-chrome-ai.git`.

```bash
scripts/build_portable_app.sh
```

## 4. Runtime update source priority

`Enable Chrome AI.app` resolves update source in this order:

1. `ENABLE_CHROME_AI_REPO_URL` (environment override)
2. `upstream` remote URL from source checkout (when running from source)
3. Embedded `repo_url.txt` inside the `.app`
4. Built-in fallback (`https://github.com/lcandy2/enable-chrome-ai.git`)
