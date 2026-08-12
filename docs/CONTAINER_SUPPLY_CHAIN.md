# Container vulnerability and SBOM policy

Production images pass a supply-chain gate after CI succeeds and before they
are pushed to GHCR:

```text
Tests and security checks
        -> build immutable SHA-tagged images locally
        -> Trivy vulnerability scan
        -> generate CycloneDX SBOMs
        -> record image identities and SBOM checksums
        -> push approved images to GHCR
        -> publish the SBOM bundle as a workflow artifact
        -> deploy the same SHA tags
```

## Vulnerability gate

Trivy scans operating-system and language-library packages in the actual
backend and frontend production images. A fixable `HIGH` or `CRITICAL`
vulnerability fails the publish job, so neither image reaches GHCR and the
deployment job cannot start. Unfixed findings do not block automatically; they
must be reviewed, risk-recorded, monitored for a vendor fix, and addressed when
a fixed base image or package becomes available.

The scan complements `pip-audit` and Gitleaks: dependency auditing evaluates
declared Python packages, Gitleaks searches repository history for secrets, and
Trivy evaluates everything installed in the final container filesystem.

## SBOM output

The workflow produces CycloneDX JSON files for:

- `backend.cdx.json`
- `worker.cdx.json`
- `scheduler.cdx.json`
- `frontend.cdx.json`

Worker and scheduler intentionally use the exact backend image and therefore
have the same image identity and package inventory. Separate files make each
deployed service explicit for inventory, incident response, and compliance.
`service-images.txt` records that mapping, and `SHA256SUMS` protects the four
SBOM files against accidental modification.

The bundle is retained with the workflow run for 90 days and is named with the
full release commit SHA. Release evidence should retain the workflow URL,
artifact digest, image tags/digests, scan result, and production approval.

## Action security and maintenance

The Trivy and artifact actions are pinned to full commit SHAs. This is
intentional: mutable action tags can be moved, and Trivy's action ecosystem had
a supply-chain compromise in March 2026. Updates require reviewing the official
signed release, resolving its tag to the underlying commit, and changing the
pin through a reviewed pull request.

Review the scan policy at least quarterly. Do not suppress a vulnerability
globally merely to make CI pass. Document temporary exceptions with the CVE,
affected image, exploitability, compensating controls, owner, and expiration.
