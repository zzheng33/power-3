#!/bin/bash

# List of benchmark names
ecp_benchmarks=("XSBench" "miniGAN" "CRADL" "sw4lite" "Laghos" "bert_large" "UNet" "Resnet50" "lammps" "gromacs" "NAMD")
# ecp_benchmarks=("NAMD")
altis_benchmarks=("gemm" "gups" "cfd" "maxflops" "pathfinder" "bfs" "particlefilter_float" "cfd_double" "kmeans" "lavamd" "fdtd2d" "pathfinder" "nw" "particlefilter_naive" "raytracing" "srad" "sort" "where")

hec_benchmarks=("addBiasResidualLayerNorm" "aobench" "background-subtract" "chacha20" "convolution3D" "dropout" "extrema" "fft" "kalman" "knn" "relu" "softmax" "stencil3d" "zmddft" "zoom")


npb_benchmarks=('bt' 'cg' 'ep' 'ft' 'is' 'lu' 'mg' 'sp' 'ua' 'miniFE' 'LULESH' 'Nekbone')

# Base directory where benchmarks are stored
# base_dir="../data/altis_solo/"

# # Run exp_power_cap.py 5 times
# for i in {1..1}; do
#     echo "Running experiment $i..."
#     python3 exp_solo.py --suite 1

#     sleep 3  # Wait before processing
#     sudo chown -R cc:cc ../data/

    # # Create run directory inside ./data/ecp_power_cap_res/
    # run_dir="$base_dir/run${i}"
    # mkdir -p "$run_dir"

    # # Move benchmark folders from ./data/ecp_power_cap_res/ to runX
    # for benchmark in "${altis_benchmarks[@]}"; do
    #     if [ -d "$base_dir/$benchmark" ]; then
    #         mv "$base_dir/$benchmark" "$run_dir/"
    #     fi
    # done
# done


base_dir="../data/npb_solo/"

# Run exp_power_cap.py 5 times
for i in {1..1}; do
    echo "Running experiment $i..."
    python3 exp_solo.py --suite 2

    sleep 3  # Wait before processing
    sudo chown -R cc:cc ../data/


#     run_dir="$base_dir/run${i}"
#     mkdir -p "$run_dir"

#     for benchmark in "${npb_benchmarks[@]}"; do
#         if [ -d "$base_dir/$benchmark" ]; then
#             mv "$base_dir/$benchmark" "$run_dir/"
#         fi
#     done

done


