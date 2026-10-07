# Junie CLI Sandbox Kit

Docker Sandboxes v3 workload for JetBrains Junie CLI build `3579.5`, with its
bundled Java runtime. The default model is `junie-lite`. Authentication uses
your JetBrains Account; the kit does not request provider API keys.

JetBrains advertises [Junie Lite as a free model for every JetBrains account](https://junie.jetbrains.com/).
Other models depend on your account's AI entitlement and quota. Check `/model`
and `/usage` after signing in to see what your account provides.

## Quick start

Install [Docker Sandboxes](https://docs.docker.com/ai/sandboxes/get-started/)
with `sbx` v0.45 or later. The kit supports Linux AMD64 and ARM64. From the
project you want Junie to work on, run:

```sh
sbx run --name junie-project --skills off \
  docker.io/olegselajev241/junie-sandbox-kit:3579.5 .
```

Select **Continue with JetBrains account**. Junie runs inside the sandbox,
so its browser callback listens on the sandbox's localhost. Use the login
screen's manual-code option: open its manual login link in your host browser,
sign in, and paste the browser's authorization code into Junie's terminal.
Keep that code out of chat and diagnostic reports.

Use `/quit` to exit. Reopen the same sandbox with:

```sh
sbx run --name junie-project
```

Junie stores login and session state in private volumes at `~/.junie` and
`~/.local/share/junie`. Treat those volumes as credential storage. Removing
the sandbox may also remove its volumes. Project instructions remain in the
project; kit instructions are indexed in the global `~/.junie/AGENTS.md`.

The entrypoint enables Junie's brave mode inside the sandbox. Junie can modify
the mounted project. Network access is limited to the declared JetBrains
services; project dependencies may need additional kits or sandbox-scoped rules.

After signing in, select `/model` to confirm the model, then try a small
prompt such as "Reply with one short greeting without inspecting or modifying
files." Check `/usage` for the account's quota. Quit and reopen the named
sandbox to check that the login persists.

To choose another entitled model when creating a sandbox, add
`--kit-arg model=MODEL_ALIAS`. That model may consume paid quota.

## Observe authentication

The optional `auth-trace` mixin adds a local TLS interception proxy for this
sandbox. It forwards through Docker's existing policy boundary and records
allowlisted metadata: method, known JetBrains host, redacted path, HTTP status,
authentication scheme, OAuth field names, and recognized grant type.
It discards header values, query values, body values, and raw flows.

```sh
sbx run --name free-junie-login --skills off \
  --kit docker.io/olegselajev241/junie-auth-trace:1.0.0 \
  docker.io/olegselajev241/junie-sandbox-kit:3579.5 .
```

Clone this repository to use the export helper. After signing in, export the
metadata from the clone:

```sh
python3 scripts/capture-auth.py free-junie-login
```

The export is `.local/oauth-trace.jsonl`, with mode `0600`. The source is
`~/.junie/auth-trace/events.jsonl` inside the sandbox. Unknown path segments
and hosts are redacted. Browser traffic on the host is outside this trace;
the trace observes Junie's requests and token exchanges. The tracer does not
enable Junie's own debug logging or export its credential files.

To check persistence, quit Junie, run `sbx stop free-junie-login`, then reopen
it with `sbx run --name free-junie-login`. Confirm the account remains signed
in and export the trace again. A refresh exchange appears as
`grant_type: refresh_token` when Junie needs to renew its token; an immediate
restart may reuse an unexpired token.

## Test reports

Use the [test report form](https://github.com/shelajev/junie-sbx-kit/issues/new?template=test-report.yml)
to report your OS, architecture, `sbx` version, login result, selected model,
and whether a small prompt and reopening the sandbox worked. Review any
metadata before posting; keep credential files and authorization codes private.

Our first account test completed the PKCE authorization-code exchange and a
refresh exchange with HTTP 200. Seven model requests returned HTTP 200.
The service's `/auth/test` endpoint repeatedly returned HTTP 500; the cause
remains unknown. The trace does not capture model response bodies, so these
HTTP results alone do not prove that an entire coding task completed.

## Local source

```sh
git clone https://github.com/shelajev/junie-sbx-kit.git
cd junie-sbx-kit
sbx run --name junie-local --skills off "$PWD" /absolute/path/to/project
```

Docker Desktop must be running for local image builds. A Git source reference
also works if your sandbox policy permits this repository:

```sh
sbx run --name junie-git --skills off \
  git+https://github.com/shelajev/junie-sbx-kit.git /absolute/path/to/project
```

## Build and verify

The descriptor and recipe share the `junie` filename stem. Both Linux AMD64
and ARM64 archives have pinned SHA-256 checksums in `releases.sha256`. The
build runs `junie --version` as `agent` and rejects a mismatched build.
Automatic Junie updates are disabled.

```sh
docker buildx build -f junie.yaml -t junie-kit:3579.5 --load .
docker run --rm junie-kit:3579.5 --version
python3 -m unittest discover -s tests -v
```

For multi-platform conformance, install Docker's `kit-tck`, then export an OCI
layout and validate it:

```sh
docker buildx build -f junie.yaml --platform linux/amd64,linux/arm64 \
  -t junie-kit:3579.5 \
  --output type=oci,dest=.local/junie-layout,tar=false .
kit-tck validate --layout .local/junie-layout 3579.5
```

An optional local archive cache lives in `.cache/`. Place the official
`junie-release-3579.5-linux-amd64.zip` or
`junie-release-3579.5-linux-aarch64.zip` there to avoid another download.
Cached archives undergo the same checksum verification and are excluded from
Git. Updating Junie requires updating the descriptor's build default and the
matching checksums from JetBrains' release metadata.

References: [Docker kits](https://docs.docker.com/ai/sandboxes/customize/),
[Docker create-kit-v3 skill](https://github.com/docker/sandbox-kit-spec/tree/main/skills/create-kit-v3),
[Junie login](https://junie.jetbrains.com/docs/junie-cli.html),
[Junie CLI options](https://junie.jetbrains.com/docs/parameters.html).

## Publishing from main

[The workflow](.github/workflows/publish.yml) runs only on pushes to `main`.
Pull requests, tags, and manual dispatches do not start it. It checks scripts
and redaction tests, builds both architectures, validates both kits with a
pinned Docker conformance tool, then publishes and validates their digests.
Action dependencies are pinned to commit SHAs.

Repository configuration:

| Setting | Type | Value |
| --- | --- | --- |
| `DOCKERHUB_USERNAME` | Actions variable | `olegselajev241` |
| `DOCKERHUB_TOKEN` | Actions secret | Docker Hub token with read/write access |

Add the secret under **Settings → Secrets and variables → Actions**. If the
initial run stops at the configuration check, add the secret and rerun the
workflow. Subsequent pushes to `main` publish:

- `junie-sandbox-kit:3579.5` and `junie-sandbox-kit:latest`
- `junie-auth-trace:1.0.0` and `junie-auth-trace:latest`
- A `sha-<full-commit-sha>` tag for each kit

Versions come from the descriptors. A version tag pins the Junie binary
build; later kit fixes can move that tag. Use the image digest in the workflow
summary to pin the complete image. Authentication state, diagnostic exports,
and local archives are excluded from Git; publishing builds from source.

## License

The kit's source is [Apache 2.0](LICENSE). Junie itself is proprietary and
subject to [JetBrains' terms](https://github.com/JetBrains/junie/blob/main/LICENSE.md).
Bundled third-party components retain their own licenses.
