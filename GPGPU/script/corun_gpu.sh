# use core that includes logical CPU 0
cd /home/cc/power/GPGPU/script/run_benchmark/altis_script/level2
cpu=0
sib=$(cat /sys/devices/system/cpu/cpu${cpu}/topology/thread_siblings_list)
echo "Pinning ./cfd to CPUs: $sib"
taskset -c "$sib" ./nw.sh