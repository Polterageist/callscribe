#!/usr/bin/env python3
"""Create GitHub issues from docs/backlog-v1.md (epics + stories) and wire Project Callscribe.

Prerequisites:
  - `gh` CLI authenticated (repo + project scopes).
  - User project "Callscribe" under the same owner as the repo (see constants below).

Priority: the Callscribe project uses single-select **Priority** with P0/P1/P2.
Backlog rubric maps to project options (not labels):
  must -> P0, should -> P1, nice -> P2

Epic issues are added to the project without setting Priority. Stories get Priority
via `gh project item-edit`.

Sub-issues: `gh issue create` does not support --parent in current gh; this script
uses the GraphQL `addSubIssue` mutation after creating each story.

Idempotency: if any issue in the repo already has the `backlog-v1` label, the script
exits with an error unless you pass --force (not recommended).

Usage:
  python scripts/import_backlog_v1_github.py
  python scripts/import_backlog_v1_github.py --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO = "Polterageist/callscribe"
OWNER = "Polterageist"
REPO_NAME = "callscribe"
PROJECT_NUMBER = "4"
PROJECT_ID = "PVT_kwHOACo87M4BXnJt"
PRIORITY_FIELD_ID = "PVTSSF_lAHOACo87M4BXnJtzhSy2hU"
# Option ids from `gh project field-list 4 --owner Polterageist --format json`
PRIORITY_OPTION = {"must": "79628723", "should": "0a877460", "nice": "da944a9c"}

EPIC_HEADER = re.compile(r"^###\s+(E\d+)\s+—\s+(.+?)\s*$")
STORY_LINE = re.compile(
    r"^-\s+\*\*(E\d+)\.(S\d+)\s+\[(must|should|nice)\]\*\*\s+(.+?)\s*$"
)


@dataclass
class Story:
    key: str
    epic_id: str
    priority: str
    text: str


@dataclass
class Epic:
    epic_id: str
    title_line: str
    stories: list[Story]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def run_gh(args: list[str], *, dry_run: bool) -> str:
    if dry_run:
        print("+", " ".join(["gh", *args]))
        return ""
    out = subprocess.run(
        ["gh", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return out.stdout.strip()


def run_gh_json(args: list[str], *, dry_run: bool) -> dict:
    if dry_run:
        print("+", " ".join(["gh", *args]))
        return {}
    out = subprocess.run(
        ["gh", *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(out.stdout)


def gql_issue_node_id(*, owner: str, repo: str, number: int, dry_run: bool) -> str:
    if dry_run:
        return f"DRYRUN_NODE_{number}"
    query = (
        "query($o:String!,$n:String!,$i:Int!){repository(owner:$o,name:$n){"
        "issue(number:$i){id}}}"
    )
    raw = subprocess.run(
        [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={query}",
            "-f",
            f"o={owner}",
            "-f",
            f"n={repo}",
            "-F",
            f"i={number}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    data = json.loads(raw.stdout)
    node = data["data"]["repository"]["issue"]
    if not node:
        raise SystemExit(f"No GraphQL node for issue #{number}")
    return node["id"]


def gql_add_sub_issue(*, parent_id: str, child_id: str, dry_run: bool) -> None:
    if dry_run:
        print("+ addSubIssue parent=", parent_id[:20], "... child=", child_id[:20], "...")
        return
    mutation = (
        "mutation($p:ID!,$c:ID!){addSubIssue(input:{issueId:$p,subIssueId:$c})"
        "{subIssue{number}}}"
    )
    subprocess.run(
        [
            "gh",
            "api",
            "graphql",
            "-f",
            f"query={mutation}",
            "-f",
            f"p={parent_id}",
            "-f",
            f"c={child_id}",
        ],
        check=True,
        capture_output=True,
        text=True,
    )


def parse_backlog(path: Path) -> list[Epic]:
    epics: list[Epic] = []
    current: Epic | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        m = EPIC_HEADER.match(line.strip())
        if m:
            current = Epic(epic_id=m.group(1), title_line=m.group(2).strip(), stories=[])
            epics.append(current)
            continue
        m = STORY_LINE.match(line.rstrip())
        if m and current is not None:
            eid, sid, prio, text = m.group(1), m.group(2), m.group(3), m.group(4)
            key = f"{eid}.{sid}"
            current.stories.append(Story(key=key, epic_id=eid, priority=prio, text=text))
    return epics


def epic_issue_title(epic: Epic) -> str:
    raw = epic.title_line
    lower = raw.lower()
    if lower.startswith("epic:"):
        raw = raw[5:].strip()
    return f"[Epic {epic.epic_id}] {raw}"


def story_issue_title(story: Story) -> str:
    text = story.text.strip()
    if len(text) > 200:
        text = text[:197] + "..."
    return f"[{story.key}] {text}"


def write_epic_body(epic: Epic) -> str:
    keys = "\n".join(f"- {s.key}" for s in epic.stories)
    goal = epic.title_line
    if goal.lower().startswith("epic:"):
        goal = goal[5:].strip()
    return (
        "## Backlog\n\n"
        f"- **Epic id**: {epic.epic_id}\n"
        "- **Doc**: [docs/backlog-v1.md]"
        "(https://github.com/Polterageist/callscribe/blob/main/docs/backlog-v1.md)\n\n"
        "## Goal\n\n"
        f"{goal}\n\n"
        "## Stories in this epic\n\n"
        f"{keys}\n\n"
        "## Notes\n\n"
        "_Imported by scripts/import_backlog_v1_github.py._\n"
    )


def write_story_body(story: Story, epic_issue_number: int) -> str:
    return (
        "## Backlog\n\n"
        f"- **Story id**: {story.key}\n"
        f"- **Rubric**: {story.priority}\n"
        f"- **Parent epic**: #{epic_issue_number}\n"
        "- **Doc**: [docs/backlog-v1.md]"
        "(https://github.com/Polterageist/callscribe/blob/main/docs/backlog-v1.md)\n\n"
        "## User story\n\n"
        f"{story.text}\n\n"
        "## Acceptance notes\n\n"
        "_Set Priority on Project Callscribe: must→P0, should→P1, nice→P2._\n"
    )


def create_issue(*, title: str, body: str, labels: list[str], dry_run: bool) -> tuple[int, str]:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", suffix=".md", delete=False
    ) as tmp:
        tmp.write(body)
        body_path = tmp.name
    try:
        args = [
            "issue",
            "create",
            "-R",
            REPO,
            "-t",
            title,
            "-F",
            body_path,
        ]
        for lb in labels:
            args.extend(["-l", lb])
        url = run_gh(args, dry_run=dry_run).splitlines()[-1] if not dry_run else ""
        if dry_run:
            return 0, "https://github.example.invalid/0"
        number = int(url.rstrip("/").split("/")[-1])
        return number, url
    finally:
        Path(body_path).unlink(missing_ok=True)


def add_to_project(url: str, *, dry_run: bool) -> str:
    data = run_gh_json(
        [
            "project",
            "item-add",
            PROJECT_NUMBER,
            "--owner",
            OWNER,
            "--url",
            url,
            "--format",
            "json",
        ],
        dry_run=dry_run,
    )
    return data.get("id", "")


def set_project_priority(item_id: str, rubric: str, *, dry_run: bool) -> None:
    opt = PRIORITY_OPTION[rubric]
    if dry_run:
        print(
            "+ gh project item-edit ... Priority",
            rubric,
            "->",
            opt,
            "item",
            item_id[:16],
        )
        return
    subprocess.run(
        [
            "gh",
            "project",
            "item-edit",
            "--id",
            item_id,
            "--field-id",
            PRIORITY_FIELD_ID,
            "--project-id",
            PROJECT_ID,
            "--single-select-option-id",
            opt,
        ],
        check=True,
    )


def ensure_backlog_label(*, dry_run: bool) -> None:
    if dry_run:
        print("+ gh label create backlog-v1 --force ...")
        return
    subprocess.run(
        [
            "gh",
            "label",
            "create",
            "backlog-v1",
            "--color",
            "5319E7",
            "--description",
            "Tracked in docs/backlog-v1.md import",
            "--force",
        ],
        check=False,
    )


def assert_no_prior_import(*, dry_run: bool, force: bool) -> None:
    if dry_run or force:
        return
    data = run_gh_json(
        [
            "issue",
            "list",
            "-R",
            REPO,
            "--label",
            "backlog-v1",
            "--json",
            "number",
            "--limit",
            "200",
        ],
        dry_run=False,
    )
    if data:
        raise SystemExit(
            f"Found {len(data)} issue(s) with label backlog-v1; "
            "refusing to duplicate import. Remove label or issues, or pass --force."
        )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument(
        "--force",
        action="store_true",
        help="Run even if backlog-v1 issues already exist (risk of duplicates)",
    )
    args = ap.parse_args()

    backlog_path = repo_root() / "docs" / "backlog-v1.md"
    epics = parse_backlog(backlog_path)
    if len(epics) != 10:
        raise SystemExit(f"Expected 10 epics, got {len(epics)}")
    story_count = sum(len(e.stories) for e in epics)
    if story_count != 34:
        raise SystemExit(f"Expected 34 stories, got {story_count}")

    assert_no_prior_import(dry_run=args.dry_run, force=args.force)
    ensure_backlog_label(dry_run=args.dry_run)

    epic_numbers: dict[str, int] = {}

    for epic in epics:
        title = epic_issue_title(epic)
        body = write_epic_body(epic)
        num, url = create_issue(
            title=title, body=body, labels=["backlog-v1"], dry_run=args.dry_run
        )
        epic_numbers[epic.epic_id] = num
        item_id = add_to_project(url, dry_run=args.dry_run)
        print(
            "epic",
            epic.epic_id,
            "->",
            num,
            url,
            "projectItem",
            item_id[:16] if item_id else "",
        )

    for epic in epics:
        parent_num = epic_numbers[epic.epic_id]
        parent_node = gql_issue_node_id(
            owner=OWNER, repo=REPO_NAME, number=parent_num, dry_run=args.dry_run
        )
        for story in epic.stories:
            st_title = story_issue_title(story)
            st_body = write_story_body(story, parent_num)
            snum, surl = create_issue(
                title=st_title, body=st_body, labels=["backlog-v1"], dry_run=args.dry_run
            )
            child_node = gql_issue_node_id(
                owner=OWNER, repo=REPO_NAME, number=snum, dry_run=args.dry_run
            )
            gql_add_sub_issue(parent_id=parent_node, child_id=child_node, dry_run=args.dry_run)
            item_id = add_to_project(surl, dry_run=args.dry_run)
            set_project_priority(item_id, story.priority, dry_run=args.dry_run)
            print("story", story.key, "->", snum, surl)

    print("Done. Epics:", len(epics), "stories:", story_count)


if __name__ == "__main__":
    main()
