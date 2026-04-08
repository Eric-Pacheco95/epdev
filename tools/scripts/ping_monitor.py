"""
Ping monitor for gaming sessions.
Logs latency spikes and packet loss to a timestamped file.
Usage: python ping_monitor.py [--target 8.8.8.8] [--threshold 60] [--interval 2]
"""
import subprocess
import re
import time
import argparse
import os
from datetime import datetime

def parse_args():
    p = argparse.ArgumentParser(description="Gaming session ping monitor")
    p.add_argument("--target", default="8.8.8.8", help="Host to ping (default: 8.8.8.8)")
    p.add_argument("--threshold", type=int, default=60, help="Spike threshold in ms (default: 60)")
    p.add_argument("--interval", type=float, default=2, help="Seconds between pings (default: 2)")
    p.add_argument("--log-dir", default=os.path.join(os.path.dirname(__file__), "..", "..", "data", "ping-logs"),
                    help="Directory for log files")
    return p.parse_args()

def ping_once(target):
    """Returns (latency_ms, lost) or (None, True) on failure."""
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "-w", "3000", target],
            capture_output=True, text=True, timeout=5
        )
        output = result.stdout
        # Windows ping: time=XXms or time<1ms
        m = re.search(r"time[=<](\d+)ms", output)
        if m:
            return int(m.group(1)), False
        # Check for timeout/unreachable
        if "timed out" in output.lower() or "unreachable" in output.lower():
            return None, True
        return None, True
    except Exception:
        return None, True

def main():
    args = parse_args()
    os.makedirs(args.log_dir, exist_ok=True)

    stamp = datetime.now().strftime("%Y-%m-%d_%H%M")
    log_path = os.path.join(args.log_dir, f"ping_{stamp}.log")

    print(f"=== Ping Monitor ===")
    print(f"Target:    {args.target}")
    print(f"Threshold: {args.threshold}ms")
    print(f"Interval:  {args.interval}s")
    print(f"Log:       {log_path}")
    print(f"Press Ctrl+C to stop and see summary.\n")

    total = 0
    lost = 0
    spikes = 0
    latencies = []
    spike_events = []

    with open(log_path, "w") as f:
        f.write(f"# Ping monitor: {args.target} | threshold={args.threshold}ms | started {stamp}\n")
        try:
            while True:
                ts = datetime.now().strftime("%H:%M:%S")
                ms, is_lost = ping_once(args.target)
                total += 1

                if is_lost:
                    lost += 1
                    line = f"[{ts}] LOST"
                    print(f"\033[91m{line}\033[0m")
                    f.write(line + "\n")
                elif ms >= args.threshold:
                    spikes += 1
                    latencies.append(ms)
                    spike_events.append((ts, ms))
                    line = f"[{ts}] SPIKE {ms}ms"
                    print(f"\033[93m{line}\033[0m")
                    f.write(line + "\n")
                else:
                    latencies.append(ms)
                    # Only log normal pings every 30th to keep log small
                    if total % 30 == 0:
                        f.write(f"[{ts}] {ms}ms (sample)\n")

                time.sleep(args.interval)

        except KeyboardInterrupt:
            pass

        # Summary
        duration_min = (total * args.interval) / 60
        avg = sum(latencies) / len(latencies) if latencies else 0
        max_ms = max(latencies) if latencies else 0
        min_ms = min(latencies) if latencies else 0
        loss_pct = (lost / total * 100) if total else 0

        summary = [
            "",
            "=== SESSION SUMMARY ===",
            f"Duration:     ~{duration_min:.0f} min ({total} pings)",
            f"Avg latency:  {avg:.0f}ms",
            f"Min/Max:      {min_ms}ms / {max_ms}ms",
            f"Spikes (>{args.threshold}ms): {spikes}",
            f"Packet loss:  {lost}/{total} ({loss_pct:.1f}%)",
        ]
        if spike_events:
            summary.append(f"Worst spike:  {max(spike_events, key=lambda x: x[1])[1]}ms at {max(spike_events, key=lambda x: x[1])[0]}")

        for line in summary:
            print(line)
            f.write(line + "\n")

        print(f"\nFull log: {log_path}")

if __name__ == "__main__":
    main()
