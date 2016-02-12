# ether-waker.sh - Wake a host when incoming connection on a port is
#                  detected.
# Copyright (C) 2015 Mansour Behabadi <mansour@oxplot.com>
# See http://blog.oxplot.com/wake-up-on-ssh/ for more info about this
# script.

# iptables rule

iptables -I FORWARD 1 -p tcp --dport 22 -m state --state NEW -j LOG --log-prefix EthErwAkEr

# background script

cat /proc/kmsg | while read LOG_LINE
do
  IP=`echo "$LOG_LINE" | grep 'EthErwAkEr' | grep -o 'DST=[^ ]\+' | cut -d= -f 2`
  if [ "$IP" = '' ]
  then
    continue
  fi
  MAC=`arp | egrep -F "$IP" | egrep -o '[A-F0-9]{2}(:[A-F0-9]{2}){5}'`
  if [ "$MAC" = '' ]
  then
    continue
  fi
  ether-wake "$MAC"
  #echo "I'm waking up $MAC"
done &
echo $! > /var/run/ether-waker.pid
