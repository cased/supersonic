# Supersonic

Streamlined GitHub PR automation for modern applications. Supersonic provides a high-level API for programmatically creating and managing Pull Requests, designed specifically for AI and SaaS applications that need to propose changes to user repositories.

## Table of Contents

- [Why Supersonic?](#why-supersonic)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
  - [Easiest Start](#easiest-start)
  - [Update Single File](#update-single-file)
  - [Update Multiple Files](#update-multiple-files)
  - [Using the CLI (experimental)](#using-the-cli-experimental)
- [Pull Request Configuration](#pull-request-configuration)
  - [Basic Usage](#basic-usage)
  - [Using PRConfig](#using-prconfig)
  - [Enterprise Usage](#enterprise-usage)
- [Configuration](#configuration)
  - [Full Configuration Options](#full-configuration-options)
  - [Environment Variables](#environment-variables)
- [Use Cases](#use-cases)
  - [AI-Powered Code Improvements](#ai-powered-code-improvements)
  - [Automated Documentation Updates](#automated-documentation-updates)
  - [Configuration Management](#configuration-management)
- [Development](#development)
  - [Setup](#setup)
  - [Code Style](#code-style)
- [License](#license)


## Why Supersonic?

Modern AI and SaaS applications often need to propose changes to user repositories—whether it's AI-suggested improvements, automated documentation updates, or configuration changes. However, creating Pull Requests programmatically through the GitHub API can be complex and error-prone.

Supersonic solves this:

- **Simple, High-Level API**: Create PRs with a single function call, using files or plain text content
- **Safe Defaults**: All changes are created as PRs, allowing users to review before merging
- **Enterprise Ready**: Full support for GitHub Enterprise and custom base URLs
- **Async by Default**: Built for high-performance services that need to handle multiple PR creations
- **Excessively customizable**: Full control over PR creation, set draft mode, reviewers, labels, etc.
- **Best for apps, useful for scripts too**: Plug it into your SaaS app and delight your users. Or automate internal workflows.

Common use cases:
- AI applications suggesting code improvements
- Documentation generators keeping docs in sync with code
- Configuration management tools proposing config updates
- Any service that needs to propose changes to user repositories

We use this at [Cased](https://cased.com) to support our DevOps automations.

## Installation

```bash
# Using pip with uv (recommended)
uv pip install supersonic

# Development installation
git clone https://github.com/cased/supersonic
cd supersonic
uv venv
source .venv/bin/activate
uv pip install -r requirements-dev.txt
uv pip install -e .
```

## Quick Start

### Easiest Start

First an idea of what Supersonic can do. 

Say you just want to create a PR to update a file—here's the simplest way:

```python
from supersonic import Supersonic

supersonic = Supersonic("your-github-token")

# Create a PR to update a file
pr_url = await supersonic.create_pr_from_content(
    repo="user/repo",
    content="print('hello world')",
    path="hello.py"
)

print(f"Created PR: {pr_url}")
```


`supersonic` will automatically create a branch, create a PR with changes to the upstream file called `hello.py`, 
and return the PR URL. In this case, it will also automatically generate a simple title and description for the PR. 
You'll probably want more customization, or to use files instead of strings to generate the PR—so read on.

### Update Single File

Sometimes you just want to update a single file and create a PR for it. You can either provide the content directly as a string, 
or point to a local file that contains the changes:

```python
# Update with content directly
pr_url = await supersonic.create_pr_from_content(
    repo="user/repo",
    content="print('hello')",
    path="src/hello.py",
    title="Add hello script",  # Optional
    description="Adds a simple hello world script",  # Optional
    draft=False,  # Optional, create as draft PR
    labels=["enhancement"],  # Optional labels
    reviewers=["username"]  # Optional reviewers
)

# Update a file
pr_url = await supersonic.create_pr_from_file(
    repo="user/repo",
    local_file_path="local/config.json",
    upstream_path="config/settings.json",
    title="Update configuration",  # Optional
    base_branch="develop"  # Optional, customize target branch
)
```

### Update Multiple Files

Need to update several files at once? Maybe you're updating configuration files across multiple services,
or generating documentation for multiple endpoints? The `update_files` method lets you batch changes together. In `files`, pass a dictionary of upstream file paths as keys, and content strings as values:

```python
# Update multiple files
pr_url = await supersonic.create_pr_from_files(
    repo="user/repo",
    files={
        "config/settings.json": '{"debug": true}',
        "README.md": "# Updated Docs\n\nNew content here"
    },
    title="Update configuration and docs",  # Optional
    description="""
    This PR includes two changes:
    1. Updated debug settings
    2. Refreshed documentation
    """,  # Optional
    labels=["config", "docs"],  # Optional
    reviewers=["tech-lead", "docs-team"]  # Optional
)
```

### Using the CLI (experimental)

All the same functionality is available through the command line interface, which is experimental.
This is great for scripts or when you want to quickly create PRs without writing code:

```bash
# Update file with content directly
supersonic --token ghp_xxx update-content user/repo "print('hello')" src/hello.py \
  --title "Add hello script" \
  --description "Adds a hello world script" \
  --reviewers username1,username2

# Update a single file
supersonic --token ghp_xxx update user/repo config.json config/settings.json \
  --title "Update configuration" \
  --labels config,automated

# Update multiple files
supersonic --token ghp_xxx update-files user/repo \
  -f '{"debug": true}' config/settings.json \
  -f "# Title" README.md \
  --title "Update configs and docs" \
  --draft  # Create as draft PR
```

## Pull Request Configuration

### Basic Usage

```python
# Configure PR options as keyword arguments
pr_url = await supersonic.update_content(
    repo="user/repo",
    content="print('hello')",
    path="src/hello.py",
    title="Add hello script",
    description="Adds a hello world script",
    base_branch="main",
    draft=False,
    labels=["enhancement"],
    reviewers=["username"]
)
```

### Using PRConfig

For more control and reusability, use the PRConfig class:

```python
from supersonic import PRConfig

config = PRConfig(
    title="Update configuration",  # Optional, defaults to "Automated changes"
    description="""
    This PR updates the configuration file with new settings.
    
    Changes:
    - Updated API endpoints
    - Added new feature flags
    """,  # Optional, supports markdown
    base_branch="main",
    draft=False,
    labels=["automated"],
    reviewers=["user1", "user2"],
    team_reviewers=["team1"],
    merge_strategy="squash",  # "merge", "squash", or "rebase"
    delete_branch_on_merge=True,
    auto_merge=False
)

pr_url = await supersonic.create_pr(
    repo="user/repo",
    changes={"config.json": new_config_content},
    config=config
)
```

### Enterprise Usage

```python
supersonic = Supersonic({
    "github_token": "your-token",
    "base_url": "https://github.your-company.com/api/v3",
    "app_name": "your-tool",
    "default_pr_config": {
        "base_branch": "main",
        "draft": False,
        "labels": ["automated"],
        "merge_strategy": "squash",
        "delete_branch_on_merge": True
    }
})
```

## Configuration

### Full Configuration Options

You can optionally use a configuration dictionary when creating a `Supersonic` instance.
Only the GitHub token is required, and there are many options.

```python
config = {
    # Required
    "github_token": "your-token",
    
    # Optional
    "base_url": "https://api.github.com",  # For GitHub Enterprise
    "app_name": "your-app-name",
    
    # Default PR Configuration
    "default_pr_config": {
        "title": "Automated Update",  # Optional
        "description": "Changes proposed by Supersonic",  # Optional
        "base_branch": "main",
        "draft": False,
        "labels": ["automated"],
        "reviewers": [],
        "team_reviewers": [],
        "auto_merge": False,
        "merge_strategy": "squash",
        "delete_branch_on_merge": True
    }
}

supersonic = Supersonic(config)
```

### Environment Variables

Supersonic looks for these environment variables:
- `GITHUB_TOKEN`: GitHub API token

## Use Cases

### AI-Powered Code Improvements

Perfect for AI applications that suggest code improvements. Supersonic makes it easy to turn AI suggestions into pull requests:

```python
async def handle_improvement_request(repo: str, file_path: str, user_prompt: str):
    # Your AI logic to generate improvements
    improved_code = await ai.improve_code(user_prompt)
    
    # Create PR with improvements
    supersonic = Supersonic(config)
    pr_url = await supersonic.update_content(
        repo=repo,
        content=improved_code,
        path=file_path,
        title=f"AI: {user_prompt[:50]}...",
        description="""
        AI-suggested improvements based on code analysis.
        Please review the changes carefully.
        """,
        draft=True,  # Let users review AI changes
        labels=["ai-improvement"],
        reviewers=["tech-lead"]
    )
    return pr_url
```

### Automated Documentation Updates

Keep documentation in sync with code changes:

```python
async def update_api_docs(repo: str, api_changes: Dict[str, Any]):
    # Generate updated docs
    docs = {
        "docs/api/endpoints.md": generate_endpoint_docs(api_changes),
        "docs/api/types.md": generate_type_docs(api_changes),
        "README.md": update_quickstart(api_changes)
    }
    
    # Create PR with all doc updates
    supersonic = Supersonic(config)
    pr_url = await supersonic.update_files(
        repo=repo,
        files=docs,
        title="Update API documentation",
        description="""
        # API Documentation Updates
        
        Automatically generated documentation updates based on API changes.
        """,
        labels=["documentation"],
        reviewers=["docs-team"],
        team_reviewers=["api-team"]
    )
    return pr_url
```

### Configuration Management

Manage customer configurations through PRs:

```python
async def update_customer_config(customer_id: str, new_settings: Dict):
    repo = f"customers/{customer_id}/config"
    config_json = json.dumps(new_settings, indent=2)
    
    supersonic = Supersonic(config)
    pr_url = await supersonic.update_content(
        repo=repo,
        content=config_json,
        path="settings.json",
        title="Update customer configuration",
        description=f"""
        Configuration updates for customer {customer_id}
        
        Changes:
        {format_changes(new_settings)}
        """,
        reviewers=[f"@{customer_id}-admin"],  # Auto-assign customer admin
        labels=["config-change"],
        auto_merge=True,  # Enable auto-merge if tests pass
        merge_strategy="squash"
    )
    return pr_url
```

## Development

### Setup

```bash
# Clone repository
git clone https://github.com/cased/supersonic
cd supersonic

# Create a new virtual environment
uv venv

# Install dependencies
uv pip install -r requirements-dev.txt
uv pip install -e .

# Run tests
uv run pytest
```

### Code Style

We use:
- `ruff` for linting and formatting
- `mypy` for type checking

All run in GitHub Actions on every PR.

## License

MIT License - see [LICENSE](LICENSE) file for details.
