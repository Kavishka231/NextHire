from pathlib import Path
import re


WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "deploy.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_vulnerability_gate_runs_before_registry_push():
    workflow = workflow_text()
    backend_scan = workflow.index("Scan backend image for fixable vulnerabilities")
    frontend_scan = workflow.index("Scan frontend image for fixable vulnerabilities")
    push = workflow.index("Push vulnerability-approved images to GHCR")
    assert backend_scan < push
    assert frontend_scan < push
    assert 'severity: HIGH,CRITICAL' in workflow
    assert 'exit-code: "1"' in workflow


def test_all_deployed_services_have_cyclonedx_sboms():
    workflow = workflow_text()
    for service in ("backend", "frontend", "worker", "scheduler"):
        assert f"sbom/{service}.cdx.json" in workflow
    assert "sha256sum sbom/*.cdx.json" in workflow
    assert "service-images.txt" in workflow


def test_supply_chain_actions_use_immutable_commit_pins():
    workflow = workflow_text()
    refs = re.findall(r"uses: (?:aquasecurity/trivy-action|actions/upload-artifact)@([^\s]+)", workflow)
    assert refs
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in refs)


def test_images_are_loaded_for_scanning_before_push():
    workflow = workflow_text()
    build_section, push_section = workflow.split("Push vulnerability-approved images to GHCR", 1)
    assert build_section.count("load: true") == 2
    assert "push: true" not in build_section
    assert 'docker push "$BACKEND_IMAGE"' in push_section
    assert 'docker push "$FRONTEND_IMAGE"' in push_section
