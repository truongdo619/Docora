from utils.utils import read_json_file_utf8
from ner_re_processing import convert_to_NER_model_input_format, convert_to_RE_model_input_format, convert_to_output_v2
from pdf_processing import process_pdf_to_text, convert_pdf_to_text_and_bounding_boxes
from NER.main_predict import inference
from RE.main_predict import predict_re
from crud.sqlite import user as user_crud
from crud.sqlite import document as document_crud
from models.sqlite import user as user_model
from models.sqlite import document as document_model
from utils import utils
from database import get_db
from datetime import datetime

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
gmail_app_password="goir ptrm pzau pikb"

def serialize(value):
    if isinstance(value, datetime):
        return value.strftime("%Y/%m/%d, %H:%M:%S")
    return value

def send_email(to_email,user ,document):
    # Set up the SMTP server
    smtp_host = 'smtp.gmail.com'  # Replace with your SMTP server
    smtp_port = 587  # Port for TLS
    from_email = 'polyminder.no.reply@gmail.com'  # Replace with your email
    password = gmail_app_password  # Replace with your email password
    email_title ="[Polyminder] Document Processing Notification"
    # Create the email message
    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = email_title
    current_infor = document.get_infor()
    # Attach the body with the msg instance
    filename = current_infor["filename"]
    upload_time = current_infor["upload_time"]
    entities = current_infor["entities"]
    relations = current_infor["relations"]
    pages = current_infor["pages"]
    status = current_infor["status"]
    html_content = f"""
    <html>
    <body>
        <p>Dear Mr/Mrs <b>{user.username}</b>,</p>
        <p>The processing of document with id : {document.id} has been completed . Please go check the result at you home page.</p>
        <h3>Document Details:</h3>
            <ul>
                <li><strong>Document ID:</strong> {document.id}</li>
                <li><strong>File name:</strong> {filename}</li>
                <li><strong>Submitted on:</strong> {upload_time}</li>
                <li><strong>Number of extracted Entities:</strong> {entities}</li>
                <li><strong>Number of extracted Relations:</strong> {relations}</li>
                <li><strong>Number of pages:</strong> {pages}</li>
                <li><strong>Status:</strong> {status}</li>
            </ul>
        <p> Thank you for using service of Polyminder!</P>
        <p>Best regards</p>
    </body>
    </html>
    """
    msg.attach(MIMEText(html_content, 'html'))

    # Connect to the SMTP server
    try:
        server = smtplib.SMTP(smtp_host, smtp_port)
        server.starttls()  # Use TLS for security
        server.login(from_email, password)  # Login with your email and password

        # Send the email
        server.sendmail(from_email, to_email, msg.as_string())
        print("Email sent successfully!")

    except Exception as e:
        print(f"Failed to send email. Error: {str(e)}")

    finally:
        server.quit()