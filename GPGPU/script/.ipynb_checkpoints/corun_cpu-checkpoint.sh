#!/usr/bin/env bash

cd /home/cc/power/GPGPU/script/run_benchmark/npb_script/big


cpu=0
sib=$(cat /sys/devices/system/cpu/cpu${cpu}/topology/thread_siblings_list)
online=$(cat /sys/devices/system/cpu/online)

expand() {
  awk -F, '{
    for (i=1;i<=NF;i++) {
      if ($i ~ /-/) {
        split($i,a,"-")
        for (j=a[1]; j<=a[2]; j++) printf "%s%s", (out?",":""), j, out=1
      } else {
        printf "%s%s", (out?",":""), $i, out=1
      }
    }
  }' <<<"$1"
}

sib_exp=$(expand "$sib")
all_exp=$(expand "$online")

remain=()
for c in $(echo "$all_exp" | tr ',' ' '); do
  keep=true
  for s in $(echo "$sib_exp" | tr ',' ' '); do
    [[ "$c" -eq "$s" ]] && keep=false && break
  done
  $keep && remain+=("$c")
done
remain_list=$(IFS=,; echo "${remain[*]}")


taskset -c "$remain_list" ./mg.sh


