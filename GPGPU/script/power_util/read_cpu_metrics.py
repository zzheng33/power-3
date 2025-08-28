import time
import csv
import argparse
import psutil
import subprocess
import re
import signal

def monitor_imc_throughput(benchmark_pid, interval=1.0):
    events = []
    for i in range(8):  # adjust if your platform has a different count of IMC units
        events += [
            f"uncore_imc_{i}/cas_count_read/",
            f"uncore_imc_{i}/cas_count_write/",
        ]

    perf_cmd = ["perf", "stat", "-I", str(int(interval * 1000))]
    for e in events:
        perf_cmd += ["-e", e]

    proc = subprocess.Popen(perf_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    start_time = time.time()
    data = []

    try:
        while psutil.pid_exists(benchmark_pid):
            # perf prints to stderr with one line per event each interval
            # we collect one interval worth of lines
            elapsed_time = time.time() - start_time
            total_reads_mib = 0.0
            total_writes_mib = 0.0
            lines_this_interval = 0
            expected_lines = len(events)

            while lines_this_interval < expected_lines:
                line = proc.stderr.readline()
                if not line:
                    break
                m = re.search(r"([\d\.]+)\s+MiB\s+uncore_imc_(\d+)/cas_count_(read|write)/", line)
                if m:
                    val = float(m.group(1))
                    kind = m.group(3)
                    if kind == "read":
                        total_reads_mib += val
                    else:
                        total_writes_mib += val
                    lines_this_interval += 1

            total_mib = total_reads_mib + total_writes_mib
            total_mb = total_mib * 1.04858  # MiB to MB
            data.append([elapsed_time, total_mb])
            time.sleep(0.01)
    finally:
        # clean up perf
        try:
            proc.send_signal(signal.SIGINT)
            proc.wait(timeout=1)
        except Exception:
            proc.kill()

    return data

def write_throughput_csv(output_csv, throughput_data):
    with open(output_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Time (s)", "Memory Throughput (MB/s)"])
        for t, mb in throughput_data:
            w.writerow([t, mb])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect IMC memory throughput only.")
    parser.add_argument("--pid", type=int, required=True, help="PID of the benchmark process")
    parser.add_argument("--output_csv", type=str, required=True, help="Output CSV file path")
    parser.add_argument("--interval", type=float, default=1.0, help="Sampling interval in seconds")
    args = parser.parse_args()

    throughput = monitor_imc_throughput(args.pid, args.interval)
    write_throughput_csv(args.output_csv, throughput)

