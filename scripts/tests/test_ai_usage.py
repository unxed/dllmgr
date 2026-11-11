import json
import os
import subprocess
import sys
import tempfile
import unittest

SCRIPT = os.path.join(os.path.dirname(__file__), "..", "ai-usage.py")


def msg(mid, model, inp, out, w5, w1, read):
    return {"type": "assistant", "timestamp": "2026-11-11T10:00:00Z", "version": "2.1.0", "entrypoint": "cli",
            "message": {"id": mid, "model": model, "usage": {
                "input_tokens": inp, "output_tokens": out, "cache_creation_input_tokens": w5 + w1,
                "cache_read_input_tokens": read,
                "cache_creation": {"ephemeral_5m_input_tokens": w5, "ephemeral_1h_input_tokens": w1}}}}


class AiUsageTest(unittest.TestCase):
    def run_json(self, root, *args):
        out = subprocess.run([sys.executable, "-I", SCRIPT, "--projects", root, "--json", *args],
                             check=True, capture_output=True, text=True).stdout
        return json.loads(out)

    def test_ticket_attribution_dedup_and_cost(self):
        with tempfile.TemporaryDirectory() as root:
            sub = os.path.join(root, "proj", "sess", "subagents")
            os.makedirs(sub)

            def agent(name, desc, prompt, lines):
                with open(os.path.join(sub, name + ".jsonl"), "w") as f:
                    f.write(json.dumps({"type": "user", "message": {"content": prompt}}) + "\n")
                    for line in lines:
                        f.write(json.dumps(line) + "\n")
                with open(os.path.join(sub, name + ".meta.json"), "w") as f:
                    json.dump({"description": desc}, f)

            m = msg("m1", "claude-opus-5-5", 1000000, 100000, 1000000, 0, 10000000)
            # the same message id twice (one entry per content block) counts once
            agent("agent-a", "#81 resize", "ticket #81, related to #47", [m, m])
            agent("agent-b", "#47 zoom", "ticket #47", [msg("m2", "claude-opus-5-5", 1, 1, 0, 0, 0)])
            r = self.run_json(root, "81")
            self.assertEqual([a["description"] for a in r["agents"]], ["#81 resize"])
            t = r["models"]["claude-opus-5-5"]
            self.assertEqual((t["messages"], t["input"], t["cache_write_5m"]), (1, 1000000, 1000000))
            # 1M input $4 + 0.1M output $2 + 1M 5m-write $5 + 10M read $2
            self.assertEqual(r["api_equivalent_usd"], 13.0)


if __name__ == "__main__":
    unittest.main()
