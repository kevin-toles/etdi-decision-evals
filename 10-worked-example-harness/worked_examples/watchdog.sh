#!/bin/zsh
# kill PID $1 if free+inactive+speculative memory drops below 1.5 GB
while kill -0 $1 2>/dev/null; do
  f=$(vm_stat | awk '/free|inactive|speculative/ {gsub("\\.","",$NF); s+=$NF} END {print int(s*16384/1e6)}')
  if [ $f -lt 1500 ]; then kill $1; echo "watchdog killed $1 at ${f} MB free" >> $2; exit; fi
  sleep 5
done
