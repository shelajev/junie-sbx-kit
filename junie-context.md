Junie runs as `agent` inside a Docker Sandbox. The working directory is the
mounted project. Read the project's own instructions before making changes.

The `junie` executable and its Java runtime are installed together in
`/opt/junie`. Automatic updates are disabled; updating Junie requires rebuilding
the kit. Junie state persists in `~/.junie` and `~/.local/share/junie`.

Network access follows the sandbox's policy. Provider credentials are managed
by the host proxy. Do not inspect, log, or copy credential values. When a
project needs additional services or toolchains, report the requirement to
the operator so they can add an appropriate kit or sandbox-scoped policy.

Shared kit skills are available under `/opt/junie-skills`. Project skills and
project guidelines remain in their usual Junie discovery locations.
