# Known issues

What you should know before you spend time on something. A problem that is not here: **Help ▸ Report a bug** opens a new issue with the version and your system filled in.
What a tool does and does not do (its scope, its accuracy, its cost) is in the guide, next to the tool: [docs/fields.md](docs/fields.md), [docs/interface.md](docs/interface.md);
the README has the design decisions (*Known limitations*).

## Platforms

- FielDev has **no release and no installer yet**: it is built from source with the scripts in `scripts/` (see [docs/building.md](docs/building.md)).
- **Windows** is the platform of the project it comes from. **Linux** builds with `scripts/build-linux.sh`; it has been built in a cloud container, where there is no window, so the application
  has not been looked at there.
- There is **no macOS** build.
