# Candidate data refresh

The `Refresh candidate data` GitHub Actions workflow is deliberately separate
from the regular test workflow. It runs only through **Run workflow** until an
AWS-backed candidate has been reviewed. It downloads public source data, builds
raw, processed, and Athena-ready artifacts in a run-specific directory, then
runs the offline test suite again.

Only a fully successful run uploads to:

```text
s3://<project-bucket>/candidates/run-<GitHub-run-id>-<attempt>/
```

It does not modify `data/raw`, `data/processed`, the local FastAPI app's routing
snapshot, the Athena external-table location, or the current dbt models. A
failed download, transformation, validation, test, or upload therefore cannot
replace the approved data. The workflow has a 30-minute time limit, permits
only one concurrent refresh, and opens one labelled GitHub issue for an
unresolved failure. Public Overpass capacity errors during walking-network
download are retried up to four times with 15, 30, and 60-second waits before
the candidate run fails clearly.

AWS authentication uses GitHub OpenID Connect rather than saved access keys.
The repository configuration requires two non-secret Actions variables:

| Variable | Meaning |
|---|---|
| `HERROUTE_S3_BUCKET` | Project bucket name, without `s3://` |
| `HERROUTE_GITHUB_OIDC_ROLE_ARN` | ARN of the narrowly scoped role GitHub Actions may assume |

The assumed role must allow writing only to the bucket's `candidates/` prefix
and must trust this repository's `main` branch. This repository uses GitHub's
custom OIDC subject template, which includes its immutable owner and repository
IDs; the committed trust policy contains the exact required `sub` claim.
Candidate promotion remains a separate, reviewed operation. After one candidate
refresh is successful and the cost and source behaviour are reviewed, a monthly
schedule can be added.

## Promotion

`Promote approved candidate` is another manual GitHub Actions workflow. Its
operator supplies the exact candidate key and types `PROMOTE`. The workflow
downloads the candidate from S3 and revalidates its manifest, row count,
unique IDs, date, lengths, coverage range, and transit-distance range before
copying it to a new immutable staging prefix. It refuses to overwrite a
same-day snapshot. If a previous workflow reached Athena activation but stopped
before dbt validation, a rerun can only resume when Glue already points to that
same staging prefix; it skips copying and activation, then performs the missing
dbt build. A pre-existing staging prefix that is not the current Glue location
still fails rather than being overwritten.

Only then does it move Athena's `segment_features` table to the new prefix and
run `dbt build` with short-lived GitHub OIDC credentials. If the dbt build
fails after the source location changes, the workflow restores the previous
Athena source location. Athena query completion is polled explicitly rather
than relying on an AWS CLI waiter, so the workflow works across CLI releases.
The local FastAPI route engine remains on its own
approved graph and feature snapshot; warehouse promotion does not silently
alter interactive routing data.

The promotion workflow uses a separate `HerRouteGitHubPromotion` IAM role. Its
policy is scoped to reading `candidates/`, creating new
`staging/segment_features/` snapshots, the HerRoute Athena workgroup, Glue
objects in the `herroute` database (including replacement of dbt-managed
tables), and the dbt output prefixes. It needs the
repository variable `HERROUTE_GITHUB_PROMOTION_ROLE_ARN`.
