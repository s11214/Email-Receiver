# Email Receiver
 <br>部署于路由器或者其他服务器
 <br>可部署在docker
 <br>接收pop3或者imap协议的所有邮件
 <br>docker buildx build --platform linux/arm64 -t s112144/emailreceiver:latest --load .
 <br>docker save -o emailreceiver_arm64.tar s112144/emailreceiver:latest 
