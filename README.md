# Email Receiver
 \n部署于路由器或者其他服务器
 \n可部署在docker
 \n接收pop3或者imap协议的所有邮件
 \ndocker buildx build --platform linux/arm64 -t s112144/emailreceiver:latest --load .
 \ndocker save -o emailreceiver_arm64.tar s112144/emailreceiver:latest 
