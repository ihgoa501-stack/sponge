"""Approval gates & permissions.

Three-tier chain enforced in Agent.run():

    ALLOW    — Execute immediately (read, list, search).
    CONFIRM  — Execute only with --auto-approve (write, delete, shell).
    REJECT   — Never execute (blocked operations).

Per-operation overrides via PluginMatch.approval take precedence over
Plugin.approval defaults. See plugins/base.py for the enum and Agent.run()
for enforcement logic.
"""
