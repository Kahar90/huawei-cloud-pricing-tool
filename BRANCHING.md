# Git Branching Strategy

This project follows a simplified Git Flow branching strategy.

## Branches

| Branch | Purpose | Protection |
|--------|---------|------------|
| `main` | Production-ready code | Protected - no direct commits |
| `develop` | Integration branch for features | Protected - no direct commits |
| `feature/*` | New features and enhancements | Create from `develop` |
| `bugfix/*` | Bug fixes | Create from `develop` |
| `hotfix/*` | Emergency production fixes | Create from `main` |

## Workflow

### Starting New Work

```bash
# Ensure you're on develop
git checkout develop
git pull origin develop

# Create a feature branch
git checkout -b feature/my-feature-name
```

### Naming Conventions

- **Features**: `feature/add-database-support`
- **Bug fixes**: `bugfix/fix-pricing-calculation`
- **Hot fixes**: `hotfix/urgent-region-fix`
- **Releases**: `release/v1.0.0`

### Committing Changes

Use conventional commit messages:

```
type(scope): short description

# Examples:
feat(pricing): add yearly pricing model support
fix(mapping): correct database flavor selection logic
docs(readme): update installation instructions
refactor(app): simplify pricing calculator
test(mapping): add unit tests for flavor matching
```

### Commit Types

| Type | Description |
|------|-------------|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `refactor` | Code refactoring |
| `test` | Adding/updating tests |
| `chore` | Maintenance tasks |

### Merging to Develop

```bash
# Switch to develop
git checkout develop
git pull origin develop

# Merge your feature branch
git merge feature/my-feature-name

# Push to remote
git push origin develop
```

### Creating a Release

```bash
# Create release branch from develop
git checkout develop
git checkout -b release/v1.0.0

# Final testing and fixes
# ...

# Merge to main
git checkout main
git merge release/v1.0.0
git tag -a v1.0.0 -m "Version 1.0.0"

# Merge back to develop
git checkout develop
git merge release/v1.0.0
```

## Pull Requests

1. Create branch from `develop`
2. Make commits with clear messages
3. Push branch to remote
4. Create Pull Request to `develop`
5. Request code review
6. Merge after approval

## Protected Branches

- `main`: Requires PR and approval
- `develop`: Requires PR for significant changes