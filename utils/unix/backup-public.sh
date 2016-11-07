BURL=http://localhost/sites/default/files/public-backups
mkdir -p /tmp/pb
cd /tmp/pb
echo Setting variables for rotating backups ... && M=M$(date +%m) && Q=Q$(( ($(date +%-m)-1)/3+1 )) && YYYY=Y$(date +%Y) && J14=J$(( $(date +%-j) % 14 )) && YYYYMMDD=$(date +%Y-%m-%d) && pwd && mkdir -p $M $Q $YYYY $J14 && echo $YYYYMMDD - $YYYY $Q $M $J14 - $BURL >> backup-history.txt && echo $BURL && rm -f $J14/* $YYYY/* $Q/* $M/* && set -x && curl -k -s -o $J14/latest.txt $BURL/latest.txt && LTT=$(< $J14/latest.txt) && curl -k -s -o $J14/$LTT.plain-dump.sql.txt.gz $BURL/$LTT.plain-dump.sql.txt.gz && curl -k -s -o $J14/$LTT.sanitized-dump.sql.txt.gz $BURL/$LTT.sanitized-dump.sql.txt.gz && curl -k -s -o $J14/$LTT.sanitized-restore.sql.txt.gz $BURL/$LTT.sanitized-restore.sql.txt.gz && curl -k -s -o $J14/$LTT.sites-default-files.tar.xz $BURL/$LTT.sites-default-files.tar.xz && cp $J14/* $YYYY/ && cp $J14/* $Q/ && cp $J14/* $M/
