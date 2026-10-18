#!/bin/sh
set -eu
cd -- "$(dirname -- "$0")"
g++ -O2 -Wall -Wextra -fPIC main.cpp -o frost-gpu-indicator $(pkg-config --cflags --libs Qt6Widgets Qt6DBus)
