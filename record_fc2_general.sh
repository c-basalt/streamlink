#!/bin/bash

basedir="."

recdir="$basedir/record"
logdir="$basedir/log"
outdir="$basedir/out"
url="https://live.fc2.com/$1"

mkdir -p "$recdir" "$logdir" "$outdir"

if [ ! -z "$2" ]; then
	sleep $2
fi

while :
do
	echo "${url}" $(date)
	logdate="$(date +%s)"
	logfile="$logdir/${logdate}_fc2_$1.ts.log"
	
	nice -5 streamlink --retry-streams 30 --retry-max 120 --retry-open 3 --logfile "$logfile" --loglevel debug --hls-live-restart --output "$recdir/${logdate}_fc2_$1_{author}_{time:%Y%m%d}_{time:%H%M%S}_{title}.ts" "${url}" best
	
	mv "$recdir/${logdate}_fc2_$1_"*.ts "$outdir"
	if [ $? -eq 0 ]; then
		mv "$logfile" "$outdir"
	fi
	sleep 10
done

