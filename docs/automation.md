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
unresolved failure.

AWS authentication uses GitHub OpenID Connect rather than saved access keys.
The repository configuration requires two non-secret Actions variables:

| Variable | Meaning |
|---|---|
| `HERROUTE_S3_BUCKET` | Project bucket name, without `s3://` |
| `HERROUTE_GITHUB_OIDC_ROLE_ARN` | ARN of the narrowly scoped role GitHub Actions may assume |

The assumed role must allow writing only to the bucket's `candidates/` prefix
and must trust this repository's `main` branch. Candidate promotion remains a
separate, reviewed operation. After one candidate refresh is successful and
the cost and source behaviour are reviewed, a monthly schedule can be added.
