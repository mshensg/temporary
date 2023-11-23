#!/bin/sh
PRINTF='{printf "{\"protocol\":\"%s\",\"receiving queue\":\"%s\",\"sending queue\":\"%s\",\"local address\":\"%s\",\"remote address\":\"%s\",\"state\":\"%s\",\"program\":\"%s\"}\n", $1, $2, $3, $4, $5, $6, $7}'
CONDITION='($1=="udp" || $1=="udp6") { $7=$6; $6="<n/a>" }'
CMD='eval sudo netstat -utnlp 2>/dev/null '
$CMD | awk "$FORMAT $CONDITION $PRINTF"
