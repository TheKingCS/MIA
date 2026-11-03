"""
core.work_agents
==================

Who can do the development work, and what each may do (DEC-0068/0069, step 3
of `docs/DEV_ECOSYSTEM_AUDIT.md`). Roles live in `work/agents.json`: each is
a provider (Claude Code, Ollama, Codex...), a model, a permission tier and the
documents it reads first. Roles are configuration; providers are adapters
that say what they can actually do, so nothing assumes they're alike.

Tiers (section 8): **read**, **propose**, **experiment** (change code in its
own lab worktree, run tests), **review** (judge someone else's candidate).
Approve is Zac's only and deploy isn't given to agents: neither can be
granted here, whatever the file says.
"""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGISTRY = ROOT / "work" / "agents.json"

TIERS = ("read", "propose", "experiment", "review")
NEVER_GRANTED = ("approve", "deploy")
# What each tier lets an agent do (DEC-0069).
ALLOWS = {
    "read": {"read"},
    "propose": {"read", "propose"},
    "experiment": {"read", "propose", "write"},
    "review": {"read", "review"},
}


class AgentError(ValueError):
    """A role or provider that can't do what was asked."""


@dataclass
class Provider:
    name: str
    kind: str
    can: list[str] = field(default_factory=list)
    command: str = ""
    model: str = ""

    def available(self) -> bool:
        """Installed and reachable here: a CLI on the path, or Ollama answering."""
        if self.kind == "cli":
            return bool(self.command) and shutil.which(self.command) is not None
        if self.kind == "local":  # Ollama answering, with this provider's model pulled
            import json
            import urllib.request

            try:
                with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2) as answer:
                    models = {m.get("name", "") for m in json.loads(answer.read()).get("models", [])}
            except (OSError, ValueError):
                return False
            return not self.model or self.model in models or f"{self.model}:latest" in models
        if self.kind == "mia":  # MIA herself, in this repo
            return (ROOT / "core" / "inspection.py").exists()
        return False


@dataclass
class Role:
    role: str
    provider: str
    tier: str
    reads: list[str] = field(default_factory=list)


@dataclass
class Registry:
    providers: dict[str, Provider]
    roles: dict[str, Role]

    def role(self, name: str) -> Role:
        found = self.roles.get(name)
        if found is None:
            raise AgentError(f"No role {name!r} in work/agents.json.")
        return found

    def may(self, role_name: str, act: str) -> None:
        """Refuse what the role's tier, or its provider, can't do."""
        role = self.role(role_name)
        if act in NEVER_GRANTED:
            raise AgentError(f"{act.capitalize()} is never an agent's: it's Zac's.")
        if act not in ALLOWS.get(role.tier, set()):
            raise AgentError(f"{role.role} is {role.tier}: it can't {act}.")
        provider = self.providers.get(role.provider)
        if provider is None:
            raise AgentError(f"{role.role}'s provider {role.provider!r} isn't registered.")
        if act in ("write", "review") and act not in provider.can:
            raise AgentError(f"{provider.name} can't {act}.")


def parse(data: dict) -> Registry:
    """Pure logic. The registry from the file's contents, checked."""
    providers = {name: Provider(name=name, kind=p.get("kind", ""), can=list(p.get("can", [])),
                                command=p.get("command", ""), model=p.get("model", ""))
                 for name, p in (data.get("providers") or {}).items()}
    roles = {}
    for r in data.get("roles") or []:
        tier = r.get("tier", "")
        if tier in NEVER_GRANTED:
            raise AgentError(f"{r.get('role')}: {tier} can't be given to an agent.")
        if tier not in TIERS:
            raise AgentError(f"{r.get('role')}: tier is one of {', '.join(TIERS)}.")
        if r.get("provider") not in providers:
            raise AgentError(f"{r.get('role')}: unknown provider {r.get('provider')!r}.")
        roles[r["role"]] = Role(role=r["role"], provider=r["provider"], tier=tier, reads=list(r.get("reads", [])))
    return Registry(providers=providers, roles=roles)


def load(path: Path = REGISTRY) -> Registry:
    return parse(json.loads(Path(path).read_text(encoding="utf-8")))
