# hello-world (Pulumi + K8s + GHCR)

What it does:
- App: Python HTTP server on `:8080`, returns `Hello from ${ENVIRONMENT}`.
- Image: built/pushed to GHCR as `ghcr.io/steve-todorov/hpm:<environment>`.
- Infra (Pulumi):
  - renders `k8s/deployment.yaml` template to set `ENVIRONMENT`, namespace, and image tag
  - applies it to your cluster using Pulumi Kubernetes YAML `ConfigFile`
  - creates a GitHub "Environment" with the same name as the Pulumi stack

## Stack naming rules (from workflows)
- `main` -> `staging-main`
- `production` -> `production`
- `([0-9]+)-.*` -> `staging-<number>`
- Anything else: skipped

## Required repo variables / secrets
Repo Variable:
- `PULUMI_ORG` = your Pulumi Cloud org (or user)

Repo Secrets:
- `PULUMI_ACCESS_TOKEN` = Pulumi Cloud access token
- `KUBECONFIG` = kubeconfig file contents for the target cluster
- `GH_ADMIN_TOKEN` = GitHub token for Pulumi GitHub provider (PAT typically needs `repo` scope for env APIs)

## Local run
1) [Github Container Registry Login](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry#authenticating-with-a-personal-access-token-classic)
2) Build & push (example):
   ```
   docker build -t ghcr.io/steve-todorov/hpm:staging-main .
   docker push ghcr.io/steve-todorov/hpm:staging-main
   ```
3) Deploy via Pulumi:
   ```
   cd infra
   python -m venv .venv && source .venv/bin/activate
   pip install -r requirements.txt
   export KUBECONFIG=~/.kube/config
   export GITHUB_OWNER=steve-todorov
   export GITHUB_REPOSITORY=steve-todorov/hpm
   export GITHUB_TOKEN=<token>
   pulumi login
   pulumi -C infra stack select --create "steve-todorov__hpm/staging-main"
   pulumi -C infra up
   ```
