# Devcontainer Guidance

## Overview

Devcontainers (`.devcontainer`) provide a consistent development environment by defining containerized development setups. They are particularly useful for repositories with complex dependencies or setup requirements.

## When to Use Devcontainers

Use devcontainers when:

- Your repository has complex setup requirements (multiple tools, specific versions, etc.)
- You want to ensure consistent development environments across team members
- You're working with Cloudflare Workers or Python services that benefit from containerized tooling
- You need to test against multiple runtime versions
- You want to simplify onboarding for new contributors

## Not Required

Devcontainers are **not required** by the repository standards. They are an optional tool that can improve development experience and consistency.

## Template Structure

Create a `.devcontainer` directory in your repository:

```
.devcontainer/
├── devcontainer.json
├── Dockerfile
└── docker-compose.yml (optional)
```

## Example: Node.js Devcontainer

```json
// .devcontainer/devcontainer.json
{
  "name": "Node.js",
  "image": "mcr.microsoft.com/devcontainers/javascript-node:20",
  "customizations": {
    "vscode": {
      "extensions": ["dbaeumer.vscode-eslint", "esbenp.prettier-vscode"]
    }
  },
  "postCreateCommand": "npm install"
}
```

## Example: Python Devcontainer

```json
// .devcontainer/devcontainer.json
{
  "name": "Python",
  "image": "mcr.microsoft.com/devcontainers/python:3.12",
  "customizations": {
    "vscode": {
      "extensions": ["ms-python.python", "ms-python.vscode-pylance"]
    }
  },
  "postCreateCommand": "pip install -r requirements.txt"
}
```

## Example: Cloudflare Worker Devcontainer

```json
// .devcontainer/devcontainer.json
{
  "name": "Cloudflare Worker",
  "image": "mcr.microsoft.com/devcontainers/javascript-node:20",
  "customizations": {
    "vscode": {
      "extensions": ["dbaeumer.vscode-eslint", "esbenp.prettier-vscode"]
    }
  },
  "postCreateCommand": "npm install && npm run build",
  "features": {
    "cloudflare/wrangler": {
      "version": "latest"
    }
  }
}
```

## Best Practices

1. **Keep it simple**: Start with a basic devcontainer and add complexity as needed
2. **Use official images**: Prefer official devcontainer images from Microsoft
3. **Document setup**: Add comments explaining key configuration options
4. **Test locally**: Verify the devcontainer works before committing
5. **Version dependencies**: Pin tool versions in Dockerfile or use specific image tags

## Alternatives

If devcontainers are not suitable for your repository:

- Use local development setup scripts
- Use package managers (npm, pip, etc.) with version files (`.nvmrc`, `requirements.txt`)
- Use environment-specific configuration files (`.env.local`, `.env.development`)

## Resources

- [Dev Containers Documentation](https://code.visualstudio.com/docs/devcontainers/containers)
- [Dev Container Templates](https://github.com/devcontainers/templates)
- [Cloudflare Wrangler Dev Containers](https://github.com/cloudflare/wrangler/tree/main/devtools/dev-container)