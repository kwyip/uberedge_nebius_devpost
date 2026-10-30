"""Run a credential-safe Nemotron council demonstration."""

import json

from nebius_agents import get_last_trace, plan_shift


DEMO = """City: Boston. Shift: 5:00 PM-9:30 PM.
Verified candidates:
- 5:45-6:20 PM: event departure opportunity; exact revenue unknown.
- 6:30-7:15 PM: college event 3.2 estimated driving miles away.
- 7:30-8:30 PM: restaurant demand signal 1.4 estimated driving miles away.
Operating cost and exact task price are unavailable. Do not invent them.
Build a cautious chain and explain what the worker must verify."""


if __name__ == "__main__":
    plan, model = plan_shift(DEMO)
    print("\nUBEREDGE PLAN\n")
    print(plan)
    print("\nNVIDIA MODEL VIA NEBIUS TOKEN FACTORY\n")
    print(model)
    print("\nCREDENTIAL-SAFE TRACE\n")
    print(json.dumps(get_last_trace(), indent=2))
