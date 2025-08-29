import os
import subprocess
import time
import signal
import argparse
import csv
import pandas as pd
from pathlib import Path
import psutil

SYSFS = Path("/sys/devices/system/cpu")

def expand_cpu_list(expr: str) -> list[int]:
    out = []
    for part in expr.split(","):
        if "-" in part:
            a, b = part.split("-")
            out.extend(range(int(a), int(b) + 1))
        else:
            out.append(int(part))
    return out

def read_text(p: Path) -> str:
    return p.read_text().strip()

def thread_siblings(cpu: int) -> list[int]:
    sib = read_text(SYSFS / f"cpu{cpu}/topology/thread_siblings_list")
    return sorted(expand_cpu_list(sib))

def online_cpus() -> list[int]:
    return expand_cpu_list(read_text(SYSFS / "online"))

sib0 = thread_siblings(0)   # GPU helper core (excluded)
sib1 = thread_siblings(1)   # reserved for CPU power
sib2 = thread_siblings(2)   # we will split its two threads

# pick specific threads from core 2
if len(sib2) < 2:
    raise RuntimeError("Core 2 does not have two logical siblings (no SMT?)")
t_mem = sib2[0]   # first logical thread of core 2
t_ips = sib2[1]   # second logical thread of core 2

# allowed CPUs = all online minus sib0, sib1, sib2
allowed = sorted(set(online_cpus()) - set(sib0) - set(sib1) - set(sib2))

allowed_str = ",".join(map(str, allowed))
sib1_str = ",".join(map(str, sib1))


num_gpu = 1

# Define paths and executables
home_dir = os.path.expanduser('~')
python_executable = subprocess.getoutput('which python3')  # Adjust based on your Python version

# scripts for CPU, GPU power monitoring
read_cpu_power = "./power_util/read_cpu_power.py"
read_gpu_power = "./power_util/read_gpu_power.py"
read_gpu_metrics = "./power_util/read_gpu_metrics.py"
read_cpu_ips = "./power_util/read_cpu_ips.py"
# read_mem = "./power_util/read_mem.py"
read_mem = "./power_util/read_cpu_metrics.py"
read_ips = "./power_util/read_cpu_metrics2.py"

# scritps for running various benchmarks
run_altis = "./run_benchmark/run_altis.py"
run_ecp = "./run_benchmark/run_ecp.py"
run_npb = "./run_benchmark/run_npb.py"
run_hec = "./run_benchmark/run_hec.py"



ecp_benchmarks = ['XSBench','miniGAN','CRADL','sw4lite','Laghos','bert_large','UNet','Resnet50','lammps','gromacs',"NAMD"]


npb_benchmarks = ['bt','cg','ep','ft','is','lu','mg','sp','ua','miniFE','LULESH','Nekbone']

npb_benchmarks = ['Nekbone']



hec_benchmarks = ["addBiasResidualLayerNorm", "aobench", "background-subtract", "chacha20", "convolution3D", "dropout", "extrema", "fft", "kalman", "knn", "softmax", "stencil3d", "zmddft", "zoom"]



altis_benchmarks_0 = ["maxflops"]
altis_benchmarks_1 = ['bfs','gemm','gups','pathfinder','sort']
altis_benchmarks_2 = ['cfd','cfd_double','fdtd2d','kmeans','lavamd',
                      'nw','particlefilter_float','particlefilter_naive','raytracing',
                      'srad','where']


# altis_benchmarks_0 = []
# altis_benchmarks_1 = ['sort']
# altis_benchmarks_2 = ['cfd_double','fdtd2d','particlefilter_naive',
#                       'srad']




# gpu_caps = [250, 240, 230, 220, 210, 200, 190, 180, 170, 160, 150]
# cpu_caps = [200, 190, 180, 170, 160, 150, 140]

gpu_caps = [250]
cpu_caps = [540]


MG = "g1"


# def ensure_resctrl(mg="g1"):
#     subprocess.run("sudo mount -t resctrl resctrl /sys/fs/resctrl || true", shell=True, check=False)
#     subprocess.run(f"sudo mkdir -p /sys/fs/resctrl/mon_groups/{mg}", shell=True, check=False)

# ensure_resctrl()


def run_benchmark(benchmark_script_dir,benchmark, suite, test, size,cap_type):

    def cap_exp(cpu_cap, gpu_cap, output_cpu_power, output_gpu_metrics, output_mem, output_ips):
        
        
        # # Set CPU and GPU power caps and wait for them to take effect
        # # subprocess.run([f"./power_util/gpu_fs.sh {gpu_freq}"], shell=True)
        # subprocess.run([f"./power_util/cpu_cap.sh {cpu_cap}"], shell=True)
        # subprocess.run([f"./power_util/gpu_cap.sh {gpu_cap}"], shell=True)
        
        time.sleep(0.2)  # Wait for the power caps to take effect
    
        # Run the benchmark
        start = time.time()
        if suite == "altis":
            run_benchmark_command = f"{python_executable} {run_altis} --benchmark {benchmark} --benchmark_script_dir {os.path.join(home_dir, benchmark_script_dir)}"
        elif suite == "ecp":
            run_benchmark_command = f"{python_executable} {run_ecp} --benchmark {benchmark} --benchmark_script_dir {os.path.join(home_dir, benchmark_script_dir)}"

        elif suite == "npb":
            run_benchmark_command = f"{python_executable} {run_npb} --benchmark {benchmark} --benchmark_script_dir {os.path.join(home_dir, benchmark_script_dir)}"

        elif suite == "hec":
            run_benchmark_command = f"{python_executable} {run_hec} --benchmark {benchmark} --benchmark_script_dir {os.path.join(home_dir, benchmark_script_dir)}"
        
        # benchmark_process = subprocess.Popen(run_benchmark_command, shell=True)
        
        benchmark_process = subprocess.Popen(f"taskset -c {allowed_str} {run_benchmark_command}", shell=True)
        benchmark_pid = benchmark_process.pid

        # benchmark_process = subprocess.Popen(
        #     f"taskset -c {allowed_str} {run_benchmark_command}",
        #     shell=True
        # )
        # benchmark_pid = benchmark_process.pid  # this is the actual app PID
        
        # 2. Attach the PID to resctrl monitor group
        # attach_cmd = f"echo {benchmark_pid} | sudo tee /sys/fs/resctrl/mon_groups/{MG}/tasks"
        # subprocess.run(attach_cmd, shell=True, check=True)

        # monitor cpu power
        # monitor_command_cpu = f"echo 9900 | sudo -S {python_executable} {read_cpu_power}  --output_csv {output_cpu_power} --pid {benchmark_pid} "
        monitor_command_cpu = (
            f"echo 9900 | sudo -S taskset -c {sib1_str} "
            f"{python_executable} {read_cpu_power} "
            f"--output_csv {output_cpu_power} --pid {benchmark_pid}"
        )
        monitor_process1 = subprocess.Popen(monitor_command_cpu, shell=True, stdin=subprocess.PIPE, text=True)

         # read cpu_metrics
        # monitor_command_cpu_metrics = f"echo 9900 | sudo -S {python_executable} {read_cpu_metrics}  --output_csv {output_cpu_metrics} --pid {benchmark_pid} "
#         monitor_command_cpu_metrics = (
#     f"echo 9900 | sudo -S taskset -c {sib2_str} "
#     f"{python_executable} {read_cpu_metrics} "
#     f"--output_csv {output_cpu_metrics} --pid {benchmark_pid}"
# )
#         monitor_command_mem = (
#     f"echo 9900 | sudo -S taskset -c {t_mem} "
#     f"{python_executable} {read_mem} "
#     f"--output_csv {output_mem} --pid {benchmark_pid}"
# )
#         monitor_process2 = subprocess.Popen(monitor_command_mem, shell=True, stdin=subprocess.PIPE, text=True)
        monitor_command_mem = (
            f"echo 9900 | sudo -S taskset -c {t_mem} "
            f"{python_executable} {read_mem} "
            f"--output_csv {output_mem} --pid {benchmark_pid}"
        )
        monitor_process2 = subprocess.Popen(monitor_command_mem, shell=True, stdin=subprocess.PIPE, text=True)
    
        monitor_command_ips = (
            f"echo 9900 | sudo -S taskset -c {t_ips} "
            f"{python_executable} {read_ips} "
            f"--output_csv {output_ips} --pid {benchmark_pid}"
        )
        monitor_process3 = subprocess.Popen(monitor_command_ips, shell=True, stdin=subprocess.PIPE, text=True)

        # # monitor GPU metrics
        if suite != "npb":
            monitor_command_gpu_metrics = f"echo 9900 | sudo -S {python_executable} {read_gpu_metrics}  --output_csv {output_gpu_metrics} --pid {benchmark_pid} --num_gpu {num_gpu}"
            monitor_process4 = subprocess.Popen(monitor_command_gpu_metrics, shell=True, stdin=subprocess.PIPE, text=True)

            
        benchmark_process.wait()  # Wait for the benchmark to complete

        
################## end helper function ####################


    
    for cpu_cap in cpu_caps:
        for gpu_cap in gpu_caps:
            output_cpu_power = f"../data/{suite}_solo/{benchmark}/cpu_power.csv"
            output_gpu_metrics = f"/home/cc/power/GPGPU/data/{suite}_solo/{benchmark}/gpu_metrics.csv"
            output_mem = f"../data/{suite}_solo/{benchmark}/cpu_mem.csv"
            output_ips = f"../data/{suite}_solo/{benchmark}/cpu_ips.csv"
            cap_exp(cpu_cap, gpu_cap, output_cpu_power, output_gpu_metrics, output_mem, output_ips)


    # make sure the first run has complete data
    # cpu_cap = cpu_caps[0]
    # gpu_cap = gpu_caps[0]
    # output_cpu_power = f"../data/{suite}_solo/{benchmark}/cpu_power.csv"
    # output_gpu_metrics = f"/home/cc/power/GPGPU/data/{suite}_solo/{benchmark}/gpu_metrics.csv"
    # output_mem = f"../data/{suite}_solo/{benchmark}/cpu_mem.csv"
    # output_ips = f"../data/{suite}_solo/{benchmark}/cpu_ips.csv"
    # cap_exp(cpu_cap, gpu_cap, output_cpu_power, output_gpu_metrics, output_mem, output_ips)




    # subprocess.run([f"./power_util/cpu_cap.sh 540"], shell=True)
    # subprocess.run([f"./power_util/gpu_cap.sh 250"], shell=True)
    # # subprocess.run([f"./power_util/gpu_fs.sh 1410"], shell=True)


if __name__ == "__main__":
   # Set up command line argument parsing
    parser = argparse.ArgumentParser(description='Run benchmarks and monitor power consumption.')
    parser.add_argument('--benchmark', type=str, help='Optional name of the benchmark to run', default=None)
    parser.add_argument('--test', type=int, help='whether it is a test run', default=None)
    parser.add_argument('--suite', type=int, help='0 for ECP, 1 for ALTIS, 2 for npb+ecp', default=1)
    parser.add_argument('--benchmark_size', type=int, help='0 for big, 1 for small', default=0)
    parser.add_argument('--cap_type', type=int, help='0 for cpu, 1 for gpu, 2 for dual', default=2)
    parser.add_argument('--num_gpu', type=int, default=1)

    args = parser.parse_args()
    benchmark = args.benchmark
    test = args.test
    suite = args.suite
    benchmark_size = args.benchmark_size
    cap_type = args.cap_type
    num_gpu = args.num_gpu


    if suite == 0 or suite ==4:
        benchmark_script_dir = f"power/GPGPU/script/run_benchmark/ecp_script"
        # single test
        if benchmark:
            run_benchmark(benchmark_script_dir, benchmark,"ecp",test,benchmark_size,cap_type)
        # run all ecp benchmarks
        else:
            for benchmark in ecp_benchmarks:
                run_benchmark(benchmark_script_dir, benchmark,"ecp",test,benchmark_size,cap_type)
    

    if suite == 1 or suite ==4:
        # Map of benchmarks to their paths
        benchmark_paths = {
            "level0": altis_benchmarks_0,
            "level1": altis_benchmarks_1,
            "level2": altis_benchmarks_2
        }
    
        if benchmark:
            # Find which level the input benchmark belongs to
            found = False
            for level, benchmarks in benchmark_paths.items():
                if benchmark in benchmarks:
                    benchmark_script_dir = f"power/GPGPU/script/run_benchmark/altis_script/{level}"
                    run_benchmark(benchmark_script_dir, benchmark,"altis",test,benchmark_size,cap_type)
                    found = True
                    break
        else:
    
            for benchmark in altis_benchmarks_0:
                if benchmark_size==0:
                    benchmark_script_dir = "power/GPGPU/script/run_benchmark/altis_script/level0"
                else:
                    benchmark_script_dir = "power/GPGPU/script/run_benchmark/altis_script/level0"
                run_benchmark(benchmark_script_dir, benchmark,"altis",test,benchmark_size,cap_type)
            
            
            for benchmark in altis_benchmarks_1:
                if benchmark_size==0:
                    benchmark_script_dir = "power/GPGPU/script/run_benchmark/altis_script/level1"
                else:
                    benchmark_script_dir = "power/GPGPU/script/run_benchmark/altis_script/level1"
                run_benchmark(benchmark_script_dir, benchmark,"altis",test,benchmark_size,cap_type)
            
            
            for benchmark in altis_benchmarks_2:
                if benchmark_size==0:
                    benchmark_script_dir = "power/GPGPU/script/run_benchmark/altis_script/level2"
                else:
                    benchmark_script_dir = "power/GPGPU/script/run_benchmark/altis_script/level2"
                run_benchmark(benchmark_script_dir, benchmark,"altis",test,benchmark_size,cap_type)

    if suite == 2 or suite == 4:
        benchmark_script_dir = f"power/GPGPU/script/run_benchmark/npb_script/big/"
        if benchmark_size==1:
            benchmark_script_dir = f"power/GPGPU/script/run_benchmark/npb_script/small/"
        # single test
        if benchmark:
            run_benchmark(benchmark_script_dir, benchmark,"npb",test,benchmark_size,cap_type)
        # run all ecp benchmarks
        else:
            for benchmark in npb_benchmarks:
                run_benchmark(benchmark_script_dir, benchmark,"npb",test,benchmark_size,cap_type)


    if suite == 3 or suite == 4:
        benchmark_script_dir = f"power/GPGPU/script/run_benchmark/hec_script"
         # single test
        if benchmark:
            run_benchmark(benchmark_script_dir, benchmark,"hec",test,benchmark_size,cap_type)
        # run all ecp benchmarks
        else:
            for benchmark in hec_benchmarks:
                run_benchmark(benchmark_script_dir, benchmark,"hec",test,benchmark_size,cap_type)






