import imaplib
import smtplib
import email
import base64
import os
import sqlite3
from time import sleep
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import subprocess
import logging

# MAX_SCORE = 89

con = sqlite3.connect('results.db')
cur = con.cursor()
cur.execute('DROP TABLE results')
cur.execute('CREATE TABLE results (surname TEXT, name TEXT, group_num INTEGER, score INTEGER, ass INTEGER)')
 
conn = imaplib.IMAP4_SSL('imap.gmail.com')
conn.login('artificial.ant.lab@gmail.com', 'xo4y_podick')

smptconn = smtplib.SMTP_SSL('smtp.gmail.com', 465)
smptconn.login('artificial.ant.lab@gmail.com', 'xo4y_podick')

response = MIMEMultipart('alternative')
response['Subject'] = 'Лабораторная работа'
response['From'] = 'dmlab2022'

os.chdir('/home/pidami/develop/AntGame')
logging.basicConfig(filename='.log', encoding='utf-8', level=logging.INFO)

while True:
    conn.select("inbox")
    rc, data = conn.search(None, '(UNSEEN)')
    ids = data[0]
    id_list = ids.split()

    for email_id in id_list:
        result, data = conn.fetch(email_id, "(RFC822)")
        raw_email = data[0][1]
        raw_email_string = raw_email.decode('utf-8')


        email_message = email.message_from_string(raw_email_string)
        address_from = email.utils.parseaddr(email_message['From'])[1]
        
        subject = email_message['Subject']
        logging.info(f'got message from {subject}')
        
        # response['To'] = "Check"
        # response['To'] = address_from

        res = -1

        if len(subject.split('-')) != 3:
            part_text = MIMEText(f'Неверный формат темы', 'plain')
        else:
            surname, name, group = subject.split('-')

            has_attach = False
            for part in email_message.walk():
                if part.get_content_maintype() == 'multipart':
                    continue
                if part.get('Content-Disposition') is None:
                    continue
                has_attach = True

                filename = part.get_filename()
                extension = filename.split('.')[-1]

                if extension == 'java':
                    if filename.split('.')[0] != 'Optimizer':
                        part_text = MIMEText(f'Не тот файл, нужно Optimizer.java', 'plain')

                    fp = open('src/main/java/com/play/Optimizer.java', 'wb')
                    fp.write(part.get_payload(decode=True))
                    fp.close()

                    run_test = ['mvn', 'clean', 'test']
                    p_jar = subprocess.Popen(run_test)
                    p_jar.wait()
                    if os.path.isfile('target/results.out'):
                        with open("target/results.out", "r") as score_file:  
                            score_file_text = score_file.read()                            
                        if (score_file_text == ''):
                            part_text = MIMEText('Не проходит по времени', 'plain')
                        else:
                            res = int(score_file_text)       
                            logging.info(f'run {surname}:{name} project - {res} points')
                            part_text = MIMEText(f'Отлично! программа скомпилировалась и запустилась. У тебя {res} баллов.', 'plain')
                    else:
                        part_text = MIMEText('Ошибка компиляции или не проходит по времени', 'plain')
                else:
                    part_text = MIMEText(f'Расширение должно быть .java, {filename};{filename.split(".")[-1]}', 'plain')
            if not has_attach:
                part_text = MIMEText('Нет прикрепленного файла', 'plain')

        response.attach(part_text)
        smptconn.sendmail('lab checker', address_from, response.as_string())
        logging.info(f'send email to {address_from}')

        conn.store(email_id, '+FLAGS', '\\Seen')

        if res != -1:
            ass = res # TODO: assessment formula
            ans = cur.execute(f'SELECT * FROM results WHERE surname = ? AND name = ? AND group_num = ?', (surname, name, group)).fetchall()
            if not ans:
                cur.execute(f'INSERT INTO results VALUES(?, ?, ?, ?, ?)', (surname, name, group, res, ass))
            else:
                cur.execute(f'UPDATE results SET score = ?, ass = ? WHERE surname = ? AND name = ? AND group_num = ?', (res, ass, surname, name, group))
            con.commit()
    sleep(15)
