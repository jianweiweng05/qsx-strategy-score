# Privacy Boundary

The local scorer runs the core scoring checks on your machine.

For QSX Overlay Preview, the app normalizes your upload into a daily `date,return` series before calling the hosted preview API.

```text
Only normalized date-return series are transmitted.
Raw files, filenames, strategy code, trade logs and account information remain local.
```

The free repository is designed so users can inspect the local scoring path. The hosted QSX Overlay Preview is optional.

See [Security Policy](../SECURITY.md) for vulnerability reporting and hosted API data-boundary details.
