#!/bin/bash

basedir="."
# token_args="--fc2-live-token=00000000-0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f-0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f-0f0f0f0f-0000000000-000-0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f0f"
# find the string in browser cookies (F12 -> Application -> cookies), either fcu or fcus (identical values)

recdir="$basedir/record"
logdir="$basedir/log"
outdir="$basedir/out"
url="https://live.fc2.com/$1"

mkdir -p "$recdir" "$logdir" "$outdir"

if [ ! -z "$2" ]; then
	sleep $2
fi

echo "${url}" $(date)

while :; do
	is_publish=$(curl -s -d "channel=1&streamid=$1" -X POST https://live.fc2.com/api/memberApi.php | grep -v is_publish\":0 |wc -l)
	# echo "${url}" $(date)   is_publish: $is_publish
	if [ $is_publish -eq 0 ]; then
		sleep 60
	else
		date
		stream_url=$(nice -5 streamlink "$token_args" --retry-streams 10 --retry-max 30 --loglevel debug --stream-url "${url}" best)
		# wait for up to ~1min until high-quality streams are available
		# "2200k" is always available first, then "3600k" appears, and then "5400k" appears. However, higher qualities are not guaranteed.
		if [ $? -ne 0 ]; then
			echo 'failed to get stream_url'
			echo "$stream_url"
			sleep 30
		else
			echo $stream_url
			if [ $(echo $stream_url|grep '/50/playlist'|wc -l) -eq 0 ]; then
				for i in $(seq 4); do
					track="best"
					date
					start_ts=$(date +%s)
					nice -5 streamlink "$token_args" --stream-url "${url}" 5400k
					if [ $? -eq 0 ]; then
						track="5400k"
						break
					else
						end_ts=$(date +%s)
						to_sleep=$(expr $start_ts - $end_ts + 15)
						echo sleep $to_sleep
						if [ $to_sleep -gt 0 ]; then
							sleep $to_sleep
						fi
					fi
				done
			else	
				track="5400k"
			fi
			echo record "${url}" "${track}"
		fi

		date
		logdate="$(date +%s)"
		logfile="$logdir/${logdate}_fc2_$1.ts.log"
		nice -5 streamlink "$token_args" --retry-open 3 --logfile "$logfile" --loglevel debug --hls-live-restart --output "$recdir/${logdate}_fc2_$1_{author}_{time:%Y%m%d}_{time:%H%M%S}_{title}.ts" "${url}" best
		echo

		mv "$recdir/${logdate}_fc2_$1_"*.ts "$outdir"
		if [ $? -eq 0 ]; then
			mv "$logfile" "$outdir"
		fi
		sleep 5
	fi
done

