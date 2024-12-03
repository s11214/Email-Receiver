# Email Receiver
 \r部署于路由器或者其他服务器
 \r可部署在docker
 \r接收pop3或者imap协议的所有邮件
 \rdocker buildx build --platform linux/arm64 -t s112144/emailreceiver:latest --load .
 \rdocker save -o emailreceiver_arm64.tar s112144/emailreceiver:latest 
