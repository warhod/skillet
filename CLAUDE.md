# Open Skills

This project uses Open Skills for consistent code quality and development standards.

## Available Skills

<available_skills>
  <skill>
    <name>git-os</name>
    <description>Enforces conventional commits, atomic changes, and GIT-OS workflow. Every agent that generates a commit must read this skill first.</description>
    <location>.open-skills/skills/git-os/SKILL.md</location>
  </skill>
  <skill>
    <name>sprint</name>
    <description>Translates ticket IDs into git branches, PR titles, and description templates automatically.</description>
    <location>.open-skills/skills/sprint/SKILL.md</location>
  </skill>
  <skill>
    <name>deploy-checklist</name>
    <description>Pre-deploy and post-deploy checklist skill. Ensures env vars, migrations, CI, rollback plan, smoke tests, and monitoring are verified before and after every deployment.</description>
    <location>.open-skills/skills/deploy-checklist/SKILL.md</location>
  </skill>
</available_skills>

## How to Use Skills

When working on tasks, check if a relevant skill is available above. To activate a skill, read its SKILL.md file to load the full instructions.

For example:
- For code quality and development guidelines, read: .open-skills/skills/git-os/SKILL.md
- For ticket automation, read: .open-skills/skills/sprint/SKILL.md
- For deployment verification, read: .open-skills/skills/deploy-checklist/SKILL.md