import base64
import json
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

# Pulumi uses the same kubeconfig kubectl uses (e.g. ~/.kube/config)
k8s_provider = k8s.Provider("k8s")

# 0) Ensure Namespace exists (Secret must be in same namespace as the Pod)
ns = k8s.core.v1.Namespace(
    f"ns-{environment}",
    metadata=k8s.meta.v1.ObjectMetaArgs(name=namespace),
    opts=ResourceOptions(provider=k8s_provider, protect=is_critical),
)

# 1) Manage GitHub Environment (created/destroyed with the stack)
gh_env = github.RepositoryEnvironment(
    f"gh-env-{environment}",
    environment=environment,
    repository=repo,
    opts=ResourceOptions(protect=is_critical),
)

# 2) Create GHCR imagePull Secret in the namespace
cfg = pulumi.Config()
ghcr_username = cfg.get("ghcrUsername") or owner
ghcr_token = cfg.require_secret("ghcrToken")  # store with: pulumi config set --secret ghcrToken ...

dockerconfigjson = ghcr_token.apply(
    lambda tok: json.dumps(
        {
            "auths": {
                "ghcr.io": {
                    "username": ghcr_username,
                    "password": tok,
                    "auth": base64.b64encode(f"{ghcr_username}:{tok}".encode()).decode(),
                }
            }
        }
    )
)

pull_secret = k8s.core.v1.Secret(
    f"ghcr-pull-secret-{environment}",
    metadata=k8s.meta.v1.ObjectMetaArgs(
        name="ghcr-pull-secret",
        namespace=ns.metadata["name"],
    ),
    type="kubernetes.io/dockerconfigjson",
    string_data={".dockerconfigjson": dockerconfigjson},
    opts=ResourceOptions(provider=k8s_provider, depends_on=[ns], protect=is_critical),
)

# 3) Deploy K8s YAML from template (rendered with ENV + image tag)
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

app = ConfigFile(
    "hello-world-yaml",
    file=str(rendered_path),
    opts=ResourceOptions(
        provider=k8s_provider,
        protect=is_critical,
        depends_on=[gh_env, pull_secret],  # ensure env + secret exist before workload apply
    ),
)

pulumi.export("environment", environment)
pulumi.export("image", image)
pulumi.export("namespace", namespace)
