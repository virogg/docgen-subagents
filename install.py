"""Install the original roles and native subagent profiles into an OpenCode project."""
import hashlib
import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKILLS = {
    "doc_gen": "md-doc-gen",
    "code_summarizer": "code-summarizer",
    "md_verifier": "md-verifier",
    "dus": "evaluate-dus",
}
AGENTS = ("md-doc-gen.md", "code-summarizer.md", "md-verifier.md")
MODEL = "opencode/deepseek-v4.1-flash-free"


def _digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def install(repository: Path, destination: Path, *, model: str = MODEL) -> dict:
    """Copy immutable source skills and role agents into destination (.opencode)."""
    repository = Path(repository).resolve()
    destination = Path(destination).resolve()
    if not repository.is_dir():
        raise NotADirectoryError(repository)
    if destination == repository or repository not in destination.parents:
        raise ValueError("destination must be inside the target repository")

    skills_root = destination / "skills"
    agents_root = destination / "agents"
    sources = [ROOT / "skillsets_original" / name for name in SKILLS]
    agent_sources = [ROOT / "agents" / name for name in AGENTS]
    targets = [skills_root / SKILLS[source.name] for source in sources]
    targets.extend(agents_root / source.name for source in agent_sources)
    targets.extend(skills_root / legacy for legacy in SKILLS)
    config_path = destination / "opencode.json"
    targets.append(config_path)
    collisions = [path for path in targets if path.exists()]
    if collisions:
        raise FileExistsError(f"Refusing to overwrite: {collisions[0]}")

    destination.mkdir(parents=True, exist_ok=True)
    for source, target in zip(sources + agent_sources, targets):
        if source.is_dir():
            shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__", ".DS_Store"))
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)

    # OpenCode resolves profile frontmatter for child models ahead of config.
    # Pin installed role metadata too; never touch original skill/helper bytes.
    for name in AGENTS:
        profile = agents_root / name
        prefix, header, body = profile.read_text().split("---", 2)
        header = re.sub(r"(?m)^model:.*$", lambda _: "model: " + json.dumps(model), header, count=1)
        profile.write_text(prefix + "---" + header + "---" + body)

    for legacy, native in SKILLS.items():
        alias = skills_root / legacy
        alias.mkdir()
        for helper in (skills_root / native).iterdir():
            if helper.is_file() and helper.name != "SKILL.md":
                (alias / helper.name).symlink_to(Path("..") / native / helper.name)

    config = {
        "$schema": "https://opencode.ai/config.json",
        "model": model,
        "snapshots": False,
        "agents": {
            **{Path(name).stem: {"model": model} for name in AGENTS},
            **{name: {"model": model} for name in ("title", "summary", "compaction")},
        },
        "permissions": [
            {"action": "skill", "resource": "*", "effect": "deny"},
            *[{"action": "skill", "resource": name, "effect": "allow"} for name in SKILLS.values()],
        ],
    }
    for role in ("code-summarizer", "md-verifier"):
        config["agents"][role]["permissions"] = [
            {"action": "subagent", "resource": "*", "effect": "deny"}
        ]
    config_path.write_text(json.dumps(config, indent=2) + "\n")

    installed = sorted(path for path in destination.rglob("*") if path.is_file())
    paths = [str(path) for path in installed]
    hashes = {str(path): _digest(path) for path in installed}
    return {"paths": paths, "hashes": hashes}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repository", type=Path)
    parser.add_argument("destination", type=Path, help="target .opencode directory")
    parser.add_argument("--model", default=MODEL)
    args = parser.parse_args()
    print(json.dumps(install(args.repository, args.destination, model=args.model), indent=2))
