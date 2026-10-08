# Frontend dependency maintenance

Install the committed dependency tree with `npm ci` from this directory.
The lockfile includes compatible security updates and current
`baseline-browser-mapping` data. No framework major-version migration is part
of this update.

## Firebase's Node transport override

Firebase 12.19.0 includes Firestore 4.17.2, which still requests
`@grpc/grpc-js ~1.9.0`. The newest matching 1.9 release remains affected by
[GHSA-m9gg-hp2v-232j](https://github.com/grpc/grpc-node/security/advisories/GHSA-m9gg-hp2v-232j)
and [GHSA-f596-whhp-79r4](https://github.com/grpc/grpc-node/security/advisories/GHSA-f596-whhp-79r4).
The package manifest scopes an override to Firestore's gRPC dependency and
pins the patched 1.14.5 release, staying within gRPC's major version 1.

The application imports Firebase App and Auth; it does not use Firestore or
run a gRPC server. The override addresses the installed dependency tree's
advisories; these audit findings do not establish exposure in the browser app.
If Firestore is added later, verify its Node transport before relying on it.
Remove the override when Firebase declares a patched gRPC dependency, then
regenerate the lockfile and rerun the checks below.

`npm audit fix --force` proposed downgrading Firebase to 9.x during this update;
that change is not necessary for this application.

## Verification

```powershell
npm.cmd ci
npm.cmd audit
npm.cmd run build
npm.cmd run lint
```

Audit results reflect the registry advisories available at the time of the
check. Keep future dependency changes separate from application behavior
changes and inspect build, lint, and audit results independently.
