# Skillet

This project uses Skillet for consistent agent guidance (CLI agents and other consumers of `AGENTS.md`).

## Available skills

<available_skills>
  <skill>
    <name>deploy-checklist</name>
    <description>Pre-deploy and post-deploy checklist skill. Ensures env vars, migrations, CI, rollback plan, smoke tests, and monitoring are verified before and after every deployment.</description>
    <location>.skillet/skills/deploy-checklist/SKILL.md</location>
  </skill>
  <skill>
    <name>git-os</name>
    <description>Enforces conventional commits, atomic changes, and GIT-OS workflow. Every agent that generates a commit must read this skill first.</description>
    <location>.skillet/skills/git-os/SKILL.md</location>
  </skill>
  <skill>
    <name>sprint</name>
    <description>Translates ticket IDs into git branches, PR titles, and description templates automatically.</description>
    <location>.skillet/skills/sprint/SKILL.md</location>
  </skill>
</available_skills>

## How to use

When a task matches a skill, read that skill's `SKILL.md` at the path in `<location>` before acting.