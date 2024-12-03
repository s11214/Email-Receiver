import imaplib
import poplib
import email
from email.header import decode_header
from email.utils import parseaddr, getaddresses
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import ssl
import re

app = Flask(__name__)
CORS(app)

# 配置日志记录
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def is_valid_email(email_addr):
    """验证邮箱地址格式"""
    regex = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(regex, email_addr) is not None

def decode_str(s):
    """解码可能包含编码的字符串"""
    decoded_fragments = []
    for part, charset in decode_header(s):
        if isinstance(part, bytes):
            try:
                part = part.decode(charset or 'utf-8', errors='ignore')
            except Exception as e:
                logging.warning(f"解码字符串失败: {e}")
                try:
                    part = part.decode('gbk', errors='ignore')
                except Exception as e:
                    logging.warning(f"再次解码字符串失败: {e}")
                    part = part.decode('utf-8', errors='ignore')
        decoded_fragments.append(part)
    return ''.join(decoded_fragments)

def get_email_addresses(header_value):
    """解析邮件地址，处理多个地址的情况"""
    addresses = getaddresses([header_value])
    decoded_addresses = []
    for name, addr in addresses:
        name = decode_str(name).strip()
        addr = addr.strip()
        if name:
            decoded_addresses.append(f"{name} <{addr}>")
        else:
            decoded_addresses.append(addr)
    return ', '.join(decoded_addresses)

def get_email_details(msg):
    """提取单封邮件的详细信息"""
    # 解析发件人
    sender_name, sender_email = get_name_and_email(msg.get('From', ''))

    # 解析收件人
    recipient_name, recipient_email = get_name_and_email(msg.get('To', ''))

    # 解析主题
    subject = msg.get('Subject', '')
    subject = decode_str(subject)

    # 提取邮件发送时间
    date_str = msg.get('Date', '')
    email_date = parse_email_date(date_str)

    # 提取邮件正文
    body = extract_email_body(msg)

    return {
        "sender_name": sender_name,
        "sender_email": sender_email,
        "recipient_name": recipient_name,
        "recipient_email": recipient_email,
        "subject": subject,
        "body": body,
        "date": email_date
    }

def get_name_and_email(header_value):
    """解析邮件地址，返回姓名和邮箱地址"""
    addresses = getaddresses([header_value])
    if addresses:
        name, email_addr = addresses[0]
        name = decode_str(name).strip()
        email_addr = email_addr.strip()
        return name, email_addr
    else:
        return '', ''

from email.utils import parsedate_tz, mktime_tz
from datetime import datetime

def parse_email_date(date_str):
    """解析邮件日期字符串，返回包含时区的日期时间字符串"""
    parsed_date = parsedate_tz(date_str)
    if parsed_date:
        timestamp = mktime_tz(parsed_date)
        dt_utc = datetime.utcfromtimestamp(timestamp)
        # 获取时区偏移量（以秒为单位）
        tz_offset = parsed_date[9]
        # 计算时区信息
        if tz_offset is not None:
            hours_offset = tz_offset // 3600
            minutes_offset = abs(tz_offset % 3600) // 60
            # 格式化时区偏移，例如 +0800 或 -0500
            tz_str = f"{hours_offset:+03d}{minutes_offset:02d}"
        else:
            tz_str = ''
        # 格式化日期时间字符串，包含时区
        date_with_tz = dt_utc.strftime('%Y-%m-%d %H:%M:%S') + f" {tz_str}"
        return date_with_tz
    else:
        return ''

def extract_email_body(msg):
    """提取邮件正文，优先获取 HTML 内容"""
    body = ''
    if msg.is_multipart():
        # 首先尝试获取 text/html 部分
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition', ''))
            if content_type == 'text/html' and 'attachment' not in content_disposition:
                charset = part.get_content_charset()
                charset = charset or part.get_charset() or 'utf-8'
                try:
                    payload = part.get_payload(decode=True)
                    body = payload.decode(charset, errors='ignore')
                    return body.strip()  # 找到 HTML 内容后立即返回
                except Exception as e:
                    logging.warning(f"解码 HTML 邮件正文失败: {e}")
        # 如果没有找到 HTML 内容，尝试获取 text/plain 部分
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get('Content-Disposition', ''))
            if content_type == 'text/plain' and 'attachment' not in content_disposition:
                charset = part.get_content_charset()
                charset = charset or part.get_charset() or 'utf-8'
                try:
                    payload = part.get_payload(decode=True)
                    body = payload.decode(charset, errors='ignore')
                    return body.strip()
                except Exception as e:
                    logging.warning(f"解码纯文本邮件正文失败: {e}")
    else:
        # 非 multipart 邮件
        content_type = msg.get_content_type()
        if content_type in ['text/plain', 'text/html']:
            charset = msg.get_content_charset()
            charset = charset or msg.get_charset() or 'utf-8'
            try:
                payload = msg.get_payload(decode=True)
                body = payload.decode(charset, errors='ignore')
                return body.strip()
            except Exception as e:
                logging.warning(f"解码邮件正文失败: {e}")
    return body.strip()

def connect_pop3(config):
    """建立POP3连接"""
    server = None
    try:
        if config['ssl']:
            context = ssl.create_default_context()
            server = poplib.POP3_SSL(config['server'], config['port'], context=context)
            logging.info(f"使用 SSL 连接到 POP3 服务器: {config['server']}:{config['port']}")
        else:
            server = poplib.POP3(config['server'], config['port'])
            logging.info(f"使用非 SSL 连接到 POP3 服务器: {config['server']}:{config['port']}")

        server.user(config['email'])
        server.pass_(config['password'])
        logging.info(f"成功登录 POP3 服务器: {config['email']}")
        return server
    except Exception as e:
        logging.error(f"POP3连接失败: {e}")
        if server:
            try:
                server.quit()
            except Exception as quit_e:
                logging.error(f"关闭 POP3 服务器连接失败: {quit_e}")
        raise e

def fetch_pop3_emails(config):
    """通过POP3协议获取所有邮件"""
    emails = []
    try:
        server = connect_pop3(config)
        num_messages = len(server.list()[1])
        logging.info(f"共有 {num_messages} 封邮件")
        if num_messages > 0:
            for i in range(1, num_messages + 1):
                logging.info(f"正在获取第 {i} 封邮件")
                raw_email = b"\n".join(server.retr(i)[1])
                msg = email.message_from_bytes(raw_email)
                logging.debug(f"邮件原始内容: {msg.as_string()}")
                email_details = get_email_details(msg)
                logging.debug(f"邮件详情: {email_details}")
                emails.append(email_details)
        else:
            logging.info("邮箱中没有邮件")
        server.quit()
        return {"emails": emails}
    except Exception as e:
        logging.error(f"获取POP3邮件出错: {e}")
        return {"error": f"获取POP3邮件出错: {e}"}

def connect_imap(config):
    """建立IMAP连接"""
    mail = None
    try:
        if config['ssl']:
            mail = imaplib.IMAP4_SSL(config['server'], config['port'])
            logging.info(f"使用 SSL 连接到 IMAP 服务器: {config['server']}:{config['port']}")
        else:
            mail = imaplib.IMAP4(config['server'], config['port'])
            logging.info(f"使用非 SSL 连接到 IMAP 服务器: {config['server']}:{config['port']}")

        mail.login(config['email'], config['password'])
        logging.info(f"成功登录 IMAP 服务器: {config['email']}")
        return mail
    except Exception as e:
        logging.error(f"IMAP连接失败: {e}")
        if mail:
            try:
                mail.logout()
            except Exception as logout_e:
                logging.error(f"注销 IMAP 服务器连接失败: {logout_e}")
        raise e

def fetch_imap_emails(config):
    """通过IMAP协议获取所有邮件"""
    emails = []
    try:
        mail = connect_imap(config)
        mail.select('INBOX')  # 选择收件箱

        # 搜索所有邮件
        status, messages = mail.search(None, 'ALL')
        if status != 'OK':
            raise Exception("无法搜索邮件")

        messages = messages[0].split()
        num_messages = len(messages)
        logging.info(f"共有 {num_messages} 封邮件")

        if num_messages > 0:
            for num in messages:
                logging.info(f"正在获取邮件 ID: {num.decode()}")
                status, msg_data = mail.fetch(num, '(RFC822)')
                if status != 'OK':
                    logging.warning(f"无法获取邮件 ID: {num.decode()}")
                    continue

                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        logging.debug(f"邮件原始内容: {msg.as_string()}")
                        email_details = get_email_details(msg)
                        logging.debug(f"邮件详情: {email_details}")
                        emails.append(email_details)

        else:
            logging.info("邮箱中没有邮件")

        mail.logout()
        return {"emails": emails}
    except Exception as e:
        logging.error(f"获取IMAP邮件出错: {e}")
        return {"error": f"获取IMAP邮件出错: {e}"}

@app.route('/getEmails', methods=['POST'])
def get_emails_route():
    logging.debug("收到 /getEmails 请求")
    logging.debug(f"请求头: {request.headers}")
    logging.debug(f"请求数据类型: {request.content_type}")
    try:
        data = request.get_json(force=True)
    except Exception as e:
        logging.error(f"解析请求数据失败: {e}")
        return jsonify({"error": "无法解析请求数据"}), 400
    logging.debug(f"请求数据: {data}")

    if not data:
        return jsonify({"error": "无效的请求数据"}), 400

    email_user = data.get('email')
    password = data.get('password')
    server_address = data.get('server')
    port = data.get('port')
    ssl_enabled = data.get('ssl', True)
    protocol = data.get('protocol', 'POP3').upper()

    if not email_user or not password or not server_address or not port:
        return jsonify({"error": "缺少必要的参数"}), 400

    # 验证邮箱地址格式
    if not is_valid_email(email_user):
        return jsonify({"error": "无效的邮箱地址"}), 400

    # 验证端口号
    try:
        port = int(port)
        if not (0 < port < 65536):
            raise ValueError
    except ValueError:
        return jsonify({"error": "无效的端口号"}), 400

    # 验证加密方式
    if not isinstance(ssl_enabled, bool):
        return jsonify({"error": "SSL字段必须为布尔值"}), 400

    if protocol not in ['POP3', 'IMAP']:
        return jsonify({"error": "协议必须是 POP3 或 IMAP"}), 400

    config = {
        'email': email_user,
        'password': password,
        'server': server_address,
        'port': port,
        'ssl': ssl_enabled,
        'protocol': protocol
    }

    if protocol == 'POP3':
        logging.info(f"获取POP3邮件: {email_user}")
        email_data = fetch_pop3_emails(config)
    elif protocol == 'IMAP':
        logging.info(f"获取IMAP邮件: {email_user}")
        email_data = fetch_imap_emails(config)
    else:
        return jsonify({"error": "不支持的协议"}), 400

    return jsonify(email_data)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, debug=True)
