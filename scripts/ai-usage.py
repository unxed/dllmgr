#!/usr/bin/env python3
"""ai-usage: tokens and API-equivalent cost of the AI work on a ticket (#72).

Reads Claude Code transcripts (~/.claude/projects/*/<session>.jsonl and their
subagents/agent-*.jsonl). Every assistant message carries its model and token
usage; messages are counted once per message id.

Attribution: a subagent belongs to ticket N when its task description
starts with #N (or, without one, its task prompt names #N first); its whole
transcript is counted, including later resumes. An agent for "#78/#82" is
counted for each of them and marked "shared".
The coordinating main session works on many tickets at once, so it is not
split per ticket; `--session ID` prints the totals of one whole session
(main + subagents) instead.

Cost is what the same tokens would cost on the Claude API (scripts/
ai-prices.json, USD per million tokens). On a subscription plan nothing is
billed per token; the figure is for comparison only. Agents that ran in the
cloud keep their transcripts there and are not seen here.

Usage: ai-usage.py TICKET... [--projects DIR] [--json]
       ai-usage.py --session ID [--projects DIR] [--json]
"""
import argparse
import glob
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def first_prompt(path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            try:
                d = json.loads(line)
            except ValueError:
                continue
            if d.get("type") != "user":
                continue
            c = d.get("message", {}).get("content")
            if isinstance(c, str):
                return c
            if isinstance(c, list):
                return " ".join(b.get("text", "") for b in c if isinstance(b, dict))
    return ""


def ticket_of(desc, prompt):
    """The ticket(s) an agent worked on: the leading "#78/#82" of its task
    description, else the first #N of its prompt. Other tickets a prompt
    mentions as background do not count."""
    m = re.match(r"\s*#(\d+)((?:\s*/\s*#\d+)*)", desc or "")
    if m:
        return {int(x) for x in re.findall(r"\d+", m.group(0))}
    m = re.search(r"#(\d+)", prompt)
    return {int(m.group(1))} if m else set()


def usage(paths):
    """Totals per model over the transcripts, each message id once."""
    seen, models, meta = set(), {}, {"first": None, "last": None, "harness": set()}
    for path in paths:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                except ValueError:
                    continue
                if d.get("type") != "assistant":
                    continue
                m = d.get("message", {})
                u, mid = m.get("usage"), m.get("id")
                if not u or not mid or mid in seen or m.get("model") == "<synthetic>":
                    continue
                seen.add(mid)
                t = models.setdefault(m.get("model", "?"), dict.fromkeys(
                    ("messages", "input", "output", "cache_write_5m", "cache_write_1h", "cache_read"), 0))
                cc = u.get("cache_creation") or {}
                w1h = cc.get("ephemeral_1h_input_tokens", 0)
                t["messages"] += 1
                t["input"] += u.get("input_tokens", 0)
                t["output"] += u.get("output_tokens", 0)
                t["cache_write_1h"] += w1h
                t["cache_write_5m"] += u.get("cache_creation_input_tokens", 0) - w1h
                t["cache_read"] += u.get("cache_read_input_tokens", 0)
                ts = d.get("timestamp")
                if ts:
                    meta["first"] = min(meta["first"] or ts, ts)
                    meta["last"] = max(meta["last"] or ts, ts)
                if d.get("version"):
                    meta["harness"].add("Claude Code %s (%s)" % (d["version"], d.get("entrypoint", "?")))
    return models, meta


def cost(models, prices):
    total, unknown = 0.0, []
    for model, t in models.items():
        p = prices.get(model)
        if not p:
            unknown.append(model)
            continue
        total += (t["input"] * p["input"] + t["output"] * p["output"] + t["cache_write_5m"] * p["cache_write_5m"]
                  + t["cache_write_1h"] * p["cache_write_1h"] + t["cache_read"] * p["cache_read"]) / 1e6
    return total, unknown


def report(title, agents, models, meta, prices, as_json):
    usd, unknown = cost(models, prices)
    if as_json:
        print(json.dumps({"title": title, "agents": agents, "models": models, "first": meta["first"],
                          "last": meta["last"], "harness": sorted(meta["harness"]),
                          "api_equivalent_usd": round(usd, 2), "unpriced_models": unknown}, indent=2))
        return
    print("### AI usage: %s" % title)
    print()
    print("- Harness: %s" % (", ".join(sorted(meta["harness"])) or "?"))
    print("- Agents: %d%s" % (len(agents), "".join("\n  - %s%s" % (a["description"], " (shared)" if a["shared"] else "")
                                                   for a in agents)))
    print("- Time: %s .. %s" % (meta["first"], meta["last"]))
    print()
    print("| model | messages | input | output | cache write 5m | cache write 1h | cache read |")
    print("|---|---|---|---|---|---|---|")
    for model, t in sorted(models.items()):
        print("| %s | %d | %d | %d | %d | %d | %d |" % (model, t["messages"], t["input"], t["output"],
                                                       t["cache_write_5m"], t["cache_write_1h"], t["cache_read"]))
    print()
    print("API-equivalent cost: $%.2f%s (prices: scripts/ai-prices.json, %s)" % (
        usd, "" if not unknown else ", without unpriced models " + ", ".join(unknown), prices.get("_date", "?")))
    if not title.startswith("session"):
        print("Not included: the coordinating main session and cloud agents.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("tickets", nargs="*", type=int)
    ap.add_argument("--session")
    ap.add_argument("--projects", default=os.path.expanduser("~/.claude/projects"))
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    with open(os.path.join(HERE, "ai-prices.json"), encoding="utf-8") as f:
        prices = json.load(f)
    if a.session:
        paths = glob.glob(os.path.join(a.projects, "*", a.session + ".jsonl"))
        paths += glob.glob(os.path.join(a.projects, "*", a.session, "subagents", "agent-*.jsonl"))
        if not paths:
            sys.exit("no transcript for session %s under %s" % (a.session, a.projects))
        models, meta = usage(paths)
        report("session " + a.session, [], models, meta, prices, a.json)
        return
    if not a.tickets:
        ap.error("give TICKET numbers or --session ID")
    # one entry per agent: the same transcript can sit under two project dirs
    found = {}
    for path in sorted(glob.glob(os.path.join(a.projects, "*", "*", "subagents", "agent-*.jsonl"))):
        desc = None
        try:
            with open(path[:-len(".jsonl")] + ".meta.json", encoding="utf-8") as f:
                desc = json.load(f).get("description")
        except (OSError, ValueError):
            pass
        name = os.path.basename(path)
        if name not in found or (desc and not found[name][1]):
            found[name] = (path, desc)
    for n in a.tickets:
        agents, paths = [], []
        for name, (path, desc) in sorted(found.items()):
            nums = ticket_of(desc, first_prompt(path))
            if n not in nums:
                continue
            agents.append({"description": desc or name, "shared": len(nums) > 1})
            paths.append(path)
        models, meta = usage(paths)
        report("#%d" % n, agents, models, meta, prices, a.json)


if __name__ == "__main__":
    main()
