#!/bin/bash

home_dir=$HOME
benchmark_dir="/home/cc/benchmark/ECP/CPU-only/AMG2013/test"
cd ${benchmark_dir}

mpirun -n 1 ./amg2013 -n 32 32 32 -P 1 1 1