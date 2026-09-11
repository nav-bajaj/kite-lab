"""Moved to data_pipeline/master_store/audit_immutability.py (P1, 2026-09-11). This shim keeps the research task runnable."""
import os, sys
sys.path.insert(0, os.environ.get("KITE_LAB_ROOT", os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))))
if __name__ == "__main__":
    import runpy; runpy.run_module("data_pipeline.master_store.audit_immutability", run_name="__main__", alter_sys=True)
else:
    from data_pipeline.master_store.audit_immutability import *  # noqa: F401,F403
