import time
import csv
import argparse
import psutil
import subprocess
import os

# Single perf stream for both instructions and LLC misses
def monitor_ips_and_llc(benchmark_pid, ips_data, llc_data, interval=0.5):
    # perf stat CSV columns with -x , and -I are: time,value,unit,event,run,cpus
    perf_cmd = [
        "perf", "stat",
        "-I", str(int(interval * 1000)),
        "-x", ",",
        "-a",
        "-e", "instructions",
        "-e", "LLC-misses",
        "sleep", "infinity",
    ]
    proc = subprocess.Popen(perf_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    start_time = time.time()
    try:
        while psutil.pid_exists(benchmark_pid):
            elapsed_time = time.time() - start_time
            inst = None
            llc = None

            # read exactly two lines per interval
            got = 0
            while got < 2:
                line = proc.stderr.readline()
                if not line:
                    break
                parts = line.strip().split(",")
                if len(parts) < 4 or parts[0].startswith("#"):
                    continue
                # parts[1] is value, parts[2] is unit, parts[3] is event name
                val_str = parts[1].replace(" ", "")
                event = parts[3]
                try:
                    val = float(val_str)
                except ValueError:
                    val = 0.0
                if event == "instructions":
                    inst = val
                    got += 1
                elif event == "LLC-misses":
                    llc = val
                    got += 1

            ips = (inst or 0.0) / interval          # per second
            llc_rate = (llc or 0.0) / interval      # per second

            ips_data.append([elapsed_time, ips])
            llc_data.append([elapsed_time, llc_rate])

            time.sleep(0.01)
    finally:
        try:
            proc.terminate()
        except Exception:
            pass

def write_ips_llc_csv(output_csv, ips_data, llc_data):
    # align by shortest length
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    n = min(len(ips_data), len(llc_data))
    with open(output_csv, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Time (s)", "IPS", "LLC Misses"])
        for i in range(n):
            w.writerow([ips_data[i][0], ips_data[i][1], llc_data[i][1]])

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Collect instructions and LLC misses with one perf stat stream")
    parser.add_argument("--pid", type=int, required=True, help="PID of the benchmark process")
    parser.add_argument("--output_csv", type=str, required=True, help="Output CSV file path")
    parser.add_argument("--interval", type=float, default=0.5, help="Sampling interval in seconds")
    args = parser.parse_args()

    ips_data = []
    llc_data = []

    # no extra threads needed
    monitor_ips_and_llc(args.pid, ips_data, llc_data, args.interval)
    write_ips_llc_csv(args.output_csv, ips_data, llc_data)
