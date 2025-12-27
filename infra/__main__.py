import os
from pathlib import Path

import pulumi
from pulumi import ResourceOptions
import pulumi_kubernetes as k8s
from pulumi_kubernetes.yaml.v2 import ConfigFile
import pulumi_github as github

# Convention: stack name == environment name == image tag
stack = pulumi.get_stack()
environment = stack

# "kept at all cost"
is_critical = environment in ("staging-main", "production")

# Repo context (CI provides GITHUB_REPOSITORY=owner/repo)
repo_full = os.getenv("GITHUB_REPOSITORY") or pulumi.Config().require("githubRepository")
owner, repo = repo_full.split("/", 1)

image = f"ghcr.io/{repo_full}:{environment}"
namespace = f"hello-world-{environment}"

# 1) Manage GitHub Environment (created/destroyed with the stack)
# Requires GitHub provider auth via env vars (GITHUB_TOKEN, GITHUB_OWNER) or provider config.
gh_env = github.RepositoryEnvironment( f"gh-env-{environment}",
    environment=environment,
    repository=repo,
    opts=ResourceOptions(protect=is_critical),
)

# 2) Deploy K8s YAML from template (rendered with ENV + image tag)
root = Path(__file__).resolve().parents[1]
template_path = root / "k8s" / "deployment.yaml"

rendered_dir = Path(__file__).resolve().parent / "rendered"
rendered_dir.mkdir(exist_ok=True)
rendered_path = rendered_dir / f"deployment.{environment}.yaml"

template = template_path.read_text(encoding="utf-8")
rendered = (
    template.replace("{{ENVIRONMENT}}", environment)
    .replace("{{NAMESPACE}}", namespace)
    .replace("{{IMAGE}}", image)
)
rendered_path.write_text(rendered, encoding="utf-8")

# Pulumi uses the same kubeconfig kubectl uses (e.g. ~/.kube/config)
k8s_provider = k8s.Provider("k8s")

app = ConfigFile(
    "hello-world-yaml",
    file=str(rendered_path),
    opts=ResourceOptions(provider=k8s_provider, protect=is_critical, depends_on=[gh_env]),
)

pulumi.export("environment", environment)
pulumi.export("image", image)
pulumi.export("namespace", namespace)
