# Contributing

Use Docker Desktop, `sbx` v0.45 or later, Python 3, and Docker's `kit-tck`.
See the README for local builds and conformance checks. Run the redaction
tests and Bash syntax checks before submitting changes:

```sh
python3 -m unittest discover -s tests -v
bash -n scripts/install.sh scripts/junie.sh scripts/startup.sh auth-trace/scripts/start.sh
```

Pull requests do not start GitHub Actions. Maintainers run the checks locally
before merging; pushes to `main` build, validate, and publish both kits.

When changing Junie versions, update `args.version.default` in `junie.yaml`
and both official release checksums in `releases.sha256`. The installer
rejects an archive without a matching checksum. Report login or model problems
with the test report template, keeping credential values out of issues.
