---
name: deploy-checklist
description: Pre-deploy and post-deploy checklist skill. Ensures env vars, migrations, CI, rollback plan, smoke tests, and monitoring are verified before and after every deployment.
license: MIT
metadata:
  author: skillet
  version: "1.0"
permissions:
  allow:
    - Bash(kubectl *)
    - Bash(docker *)
    - Bash(terraform *)
---

# Deploy Checklist — Pre & Post Deployment Verification

## Trigger

Load this skill **before any deployment** — do not proceed without reading it first:
- Running `git push` to deploy branch
- Executing CI/CD pipeline manually
- Triggering a release/deployment
- Running `kubectl apply` or similar

---

## 1. Pre-Deploy Checklist

Complete ALL items before deploying:

### Environment Variables
- [ ] All required env vars are set in deployment target
- [ ] New env vars documented in `.env.example`
- [ ] Secrets properly configured (not in code)

### Database
- [ ] Migrations are ready and tested locally
- [ ] Migration down script exists
- [ ] No unapplied migrations in pipeline

### CI/CD
- [ ] All tests passing locally
- [ ] CI pipeline green on target branch
- [ ] Build artifacts successfully created
- [ ] Linting and type-checking pass

### Code Quality
- [ ] No console.logs or debug code left
- [ ] No commented-out code in production files
- [ ] Sensitive data not hardcoded

### Dependencies
- [ ] `npm audit` / `pip audit` shows no critical vulnerabilities
- [ ] Dependency lock files updated

### Rollback Plan
- [ ] Know how to rollback (commit hash, branch, docker tag)
- [ ] Database rollback strategy defined
- [ ] Communication plan ready (team, stakeholders)

### Smoke Tests
- [ ] Basic smoke test script ready
- [ ] Health check endpoints verified
- [ ] Key user flows tested manually

---

## 2. Post-Deploy Checklist

Complete ALL items after deployment:

### Verification
- [ ] Application responding at expected URL
- [ ] Health check passing
- [ ] Logs showing no errors
- [ ] Metrics flowing to monitoring

### Smoke Tests
- [ ] Run basic smoke test script
- [ ] Key user flows working
- [ ] API endpoints responding correctly

### Monitoring
- [ ] Error rate baseline established
- [ ] No new alerts firing
- [ ] Performance metrics normal

### Communication
- [ ] Team notified of deployment
- [ ] Stakeholders informed if needed
- [ ] Deployment logged in changelog

### Rollback Ready
- [ ] If issues detected, initiate rollback within 5 minutes
- [ ] Document any issues for follow-up

---

## 3. Common Deployment Commands

### Docker
```bash
docker build -t myapp:latest .
docker tag myapp:latest registry/myapp:v1.2.3
docker push registry/myapp:v1.2.3
```

### Kubernetes
```bash
kubectl set image deployment/myapp myapp=registry/myapp:v1.2.3
kubectl rollout status deployment/myapp
```

### Serverless
```bash
serverless deploy --stage prod
```

---

## 4. Emergency Response

If deployment causes issues:

1. **Check** — Is it the code or infrastructure?
2. **Decide** — Rollback or hotfix?
3. **Act** — Execute rollback plan
4. **Communicate** — Alert team immediately
5. **Document** — What happened, why, fix

---

## 5. What Never To Do

- Deploy without running tests locally
- Skip the pre-deploy checklist
- Deploy on Friday afternoon (unless hotfix)
- Ignore failing smoke tests
- Delay rollback when issues detected