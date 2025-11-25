#!/bin/bash
set -e

echo "Starting PulseAudio setup..."

pulseaudio -D --exit-idle-time=-1 --system=false

sleep 2

pactl load-module module-null-sink sink_name=virtual-sink sink_properties=device.description="Virtual_Sink"
pactl load-module module-loopback source=virtual-sink.monitor sink=virtual-sink latency_msec=1

pactl set-default-sink virtual-sink
pactl set-default-source virtual-sink.monitor

echo "PulseAudio virtual sink configured successfully"
echo "Starting application..."

exec "$@"
