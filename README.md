# Email Receiver
 <br>部署于路由器或者其他服务器
 <br>可部署在docker
 <br>接收pop3或者imap协议的所有邮件
 <br>docker buildx build --platform linux/arm64 -t s112144/emailreceiver:latest --load .
 <br>docker save -o emailreceiver_arm64.tar s112144/emailreceiver:latest 
 <br>docker load -i emailreceiver_arm64.tar
 <br>docker run -d -p 5000:5000 --name emailreceiver_container s112144/emailreceiver:latest
 <br>日志挂载到其他文件
 <br>docker run -d -p 5000:5000 --name emailreceiver_container -v /path/on/host/app.log:/app/app.log s112144/emailreceiver:latest

 在windows构建
 <br>docker build -t s112144/emailreceiver:latest .
