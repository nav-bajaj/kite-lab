"""Moved to data_pipeline/master_store/emit_pit_membership.py (P1, 2026-09-11). This shim keeps the research task runnable."""
import os, sys
sys.path.insert(0, os.environ.get("KITE_LAB_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))))
if __name__ == "__main__":
    import runpy; runpy.run_module("data_pipeline.master_store.emit_pit_membership", run_name="__main__", alter_sys=True)
else:
    from data_pipeline.master_store.emit_pit_membership import *  # noqa: F401,F403
