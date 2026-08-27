#!/usr/bin/env python3
"""Sync C's outbound bus files into assurance/bus_mirror_c/ (D-R0-30, namespace per D-R0-39)."""
import pathlib, shutil
BUS = pathlib.Path("/home/sieg/projects-wsl/ProjectFinal/.agent_bus/landing_v2")
M = pathlib.Path(__file__).resolve().parent / "bus_mirror_c"
for d in ("tickets", "acks", "completions", "heartbeat"): (M / d).mkdir(parents=True, exist_ok=True)
for f in BUS.glob("tickets/C-*.json"): shutil.copy(f, M / "tickets" / f.name)
for f in BUS.glob("acks/*.C.json"): shutil.copy(f, M / "acks" / f.name)
for f in BUS.glob("completions/*.C.json"): shutil.copy(f, M / "completions" / f.name)
if (BUS / "heartbeats/C.json").exists(): shutil.copy(BUS / "heartbeats/C.json", M / "heartbeat" / "C.json")
# remove legacy flat files (moved into namespaces)
for f in M.glob("*.json"): f.unlink()
print("mirror synced:", {d: len(list((M / d).glob('*.json'))) for d in ("tickets", "acks", "completions", "heartbeat")})
