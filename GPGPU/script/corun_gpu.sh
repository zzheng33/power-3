# use core that includes logical CPU 0
cd /home/cc/power/GPGPU/script/run_benchmark/altis_script/level2
cd /home/cc/power/GPGPU/script/run_benchmark/ecp_script

cpu=0
sib=$(cat /sys/devices/system/cpu/cpu${cpu}/topology/thread_siblings_list)

taskset -c "$sib" ./UNet.sh