#import eventlet
#eventlet.monkey_patch()
#from eventlet import wsgi
from flask import Flask, render_template, jsonify, request, url_for, session, redirect
from flask_mysqldb import MySQL
from itsdangerous import URLSafeTimedSerializer
from flask_session import Session
import MySQLdb.cursors
import re
import smtplib
from email.mime.text import MIMEText
from werkzeug.security import generate_password_hash, check_password_hash
#import requests
from flask_socketio import SocketIO
import webbrowser

app = Flask(__name__)
app.config.from_pyfile('config.py')
mysql = MySQL(app)
socketio = SocketIO(app)
Session(app)

SignedinUsers = []
RoomUsers = []
PMUsers = {}
DivData = []
conversations = []

def generate_confirmation_token(email):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=app.config['SECURITY_PASSWORD_SALT'])


def confirm_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=app.config['SECURITY_PASSWORD_SALT'],
            max_age=expiration
        )
    except:
        return False
    return email

def send_email(subject, body, recipient):
    sender_id = app.config["MAIL_SENDER"]
    psw = app.config["MAIL_APP_PASSWORD"]
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_id
    msg['To'] = recipient
    smtp_server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
    smtp_server.login(sender_id, psw)
    smtp_server.sendmail(sender_id, recipient, msg.as_string())
    smtp_server.quit()


def messageReceived(methods=['GET', 'POST']):
    print('message was received!!!')

def convertToHtml(UserList):
    DivHtml = ""
    for x in UserList:
        DivHtml = DivHtml + "<a href=\"#\" onclick=\"initiatePM(\'" + x + "\')\">" + x + "</a><br>"
    return DivHtml

def existsInPM(user):
    hit = False
    for x in PMUsers:
        if PMUsers[x] == session['username']:
            hit = True
            break
    return hit


def pmParties(message):
    message = message.replace(" ","")
    message = message.replace("\'","")
    message = message.strip("{}")
    newstr = re.split(":|,", message)
    return newstr

@socketio.on('connect')
def connect():
    if not session['username'] in RoomUsers:
        RoomUsers.append(session['username'])
        DivData.append(session['username'])
        retHtml = convertToHtml(DivData)
        socketio.emit('UList', {'Ldata': retHtml})
        socketio.emit('UStatus', {'SMsg': session['username'] + ' has joined the room'})
    else:
        PMUsers[request.sid] = session['username']


@socketio.on('disconnect')
def disconnect():
    if not request.sid in PMUsers:
        RoomUsers.remove(session['username'])
        DivData.remove(session['username'])
        retHtml = convertToHtml(DivData)
        socketio.emit('UList', {'Ldata': retHtml})
        socketio.emit('UStatus', {'SMsg': session['username'] + ' has left the room'})
    else:
        del(PMUsers[request.sid])
        socketio.emit('PMStatus', {'SMsg': session['username'] + ' has left the chat'})

@socketio.on('my event')
def handle_my_custom_event(json, methods=['GET', 'POST']):
    print('received my event: ' + str(json))
    socketio.emit('my response', json, callback=messageReceived)

@socketio.on('private message')
def handle_my_custom_event(json, methods=['GET', 'POST']):
    print('received my event: ' + str(json))
    socketio.emit('prv msg', json, callback=messageReceived)

@socketio.on('PM request')
def sendPMRequest(json, methods=['GET', 'POST']):
    req = str(json)
    print('received my event: ' + req)
    parties = pmParties(req)
    if existsInPM(parties[1]):
        #return render_template('exception-page.html', DispMsg='Oops ! You can have one private chat at a time')
        socketio.emit('PM exception', {'pmuser': parties[1]})
    else:
        socketio.emit('send request', json, callback=messageReceived)
    
@socketio.on('PM response')
def sendPMRequest(json, methods=['GET', 'POST']):
    print('received my event: ' + str(json))
    socketio.emit('send response', json, callback=messageReceived)

@app.route("/")
def main():
    if not session.get('username'):
        return render_template('index.html')
    else:
        return redirect(url_for('getDashboard'))

@app.route('/ChatMain/')
def getChatPage():
    if session.get('username') in RoomUsers:
        return render_template('exception-page.html', DispMsg='You are already in this chat room')
    elif not session.get('username'):
        return redirect(url_for('main'))
    else:
        return render_template('ChatRoom.html', lp=session['username'])
    
@app.route('/privatemsg/')
def getPMWindow():
    if not session.get('username'):
        return redirect(url_for('main'))
    else:
        return render_template('pm.html')

@app.route('/dashboard/')
def getDashboard():
    if not session.get('username'):
        return redirect(url_for('main'))
    else:
        return render_template('dashboard.html', us=session['username'])

@app.route("/signup/")
def getSignupPage():
    return render_template('signup.html')

@app.route('/login/', methods =['GET', 'POST'])
def signin():    
    msg = ''
    if request.method == 'POST' and 'uname' in request.form and 'psw' in request.form:
        username = request.form['uname']
        password = request.form['psw']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE UserId = % s', (username, ))
        account = cursor.fetchone()

        if account:
            
            if not check_password_hash(account['Pass'], password):
                msg = "Incorrect password"
                return render_template('index.html', lstatus = msg, runame=username, rpsw=password)
            
            elif account['confirmed']=="No":
                return render_template('notify.html', RegUser=account['UserId'])
            
            elif account['UserId'] in SignedinUsers:
                return render_template('exception-page.html', DispMsg='This user has already signed in from another device')
            
            else:    
                session['username'] = account['UserId'] 
                msg = "Logged in successfully !"
                socketio.emit('UStatus', {'SMsg': session['username'] + ' has signed in'})
                SignedinUsers.append(session['username'])
                if session['username'] in RoomUsers:
                    DivData.append(session['username'])
                    retHtml = convertToHtml(DivData)
                    socketio.emit('UList', {'Ldata': retHtml})
                return redirect(url_for('getDashboard'))
                
        else:
            msg = "Incorrect username"
            return render_template('index.html', lstatus = msg, runame=username, rpsw=password)
    else:
         return redirect(url_for('main'))
        

@app.route('/logout/', methods =['GET', 'POST'])
def signout():
    if session.get('username'):
        socketio.emit('UStatus', {'SMsg': session['username'] + ' has signed out'})
        #SignedinUsers.remove(session['username'])
        if session['username'] in DivData:
            DivData.remove(session['username'])
        retHtml = convertToHtml(DivData)
        socketio.emit('UList', {'Ldata': retHtml})
        session.pop('username', None)
        return redirect(url_for('main'))
    else:
        return redirect(url_for('main'))
    
    
@app.route('/register/', methods =['GET', 'POST'])
def register():
    msg = ''
    isValidData = True
    regex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    if (request.method == 'POST' and 'fname' in request.form and 'lname' in request.form and 'email' in request.form 
    and 'ccode' in request.form and 'acode' in request.form and 'phone' in request.form and 'uid' in request.form 
    and 'pass' in request.form and 'conpass' in request.form):
        fname = request.form['fname']
        lname = request.form['lname']
        email = request.form['email']
        ccode = request.form['ccode']
        acode = request.form['acode']
        phone = request.form['phone']
        uid = request.form['uid']
        psw = request.form['pass']
        conpass = request.form['conpass']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM users WHERE UserId = % s OR Email = % s', (uid, email, ))
        account = cursor.fetchone()
        if account:
            msg = "* Account with this username/email already exists !"
            isValidData = False
        else:
            if not (fname.isalpha() and lname.isalpha()):
                msg = "* Invalid first or last name<br>"
                isValidData = False
            if not re.fullmatch(regex, email):
                msg += "* Invalid email address<br>"
                isValidData = False
            if not (ccode.isdigit() and acode.isdigit() and phone.isdigit()):
                msg += "* Invalid phone no.<br>"
                isValidData = False
            if not re.match(r'[A-Za-z0-9]+', uid):
                msg += "* Username must contain only characters and numbers<br>"
                isValidData = False
            if psw != conpass:
                msg += "* The passwords don't match<br>"
                isValidData = False
            if len(psw) < 6:
                msg += "* Password must be at least 6 characters long<br>"
                isValidData = False

        if isValidData:
            hasch = generate_password_hash(psw)
            cursor.execute('INSERT INTO users VALUES (%s, %s, %s, %s, %s, %s, %s)', (uid, fname, lname, email, '+' + ccode + acode + phone, hasch, 'No'))
            mysql.connection.commit()
            token = generate_confirmation_token(email)
            confirm_url = url_for('confirm_email', token=token, _external=True)
            mailtext = "Welcome " + uid + ",\n\n" + "Thank you for registering on Chatterbox. Here, you can chit chat and socialize with thousands of other users worldwide. It has a bunch of other exciting features like screen sharing, audio/video calls and much more.\nPlease follow this link to activate your account:\n\n" + confirm_url
            subject = "Welcome to Chatterbox ! "
            send_email(subject, mailtext, email)
            
            return render_template('notify.html', RegUser=uid)
        else:
            return render_template('signup.html', regstatus = msg, rfname=fname, rlname=lname, remail=email, 
                           rccode=ccode, racode=acode, rphone=phone, ruid=uid, rpsw=psw, rconpass=conpass)
    else:
        return redirect(url_for('main'))

@app.route("/confirm/<token>")
#@login_required
def confirm_email(token):
    try:
        email = confirm_token(token)
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)   
        cursor.execute('SELECT * FROM users WHERE Email = % s', (email, ))
        account = cursor.fetchone()

        if account and account['confirmed'] == "No":
            cursor.execute('UPDATE users SET confirmed = \'Yes\' where Email = % s', (email, ) )
            mysql.connection.commit()
            return render_template('email-confirm.html',confirmation_msg="Congratulations ! Your account has been sucessfully activated.")    
        else:
            return render_template('email-confirm.html',confirmation_msg="Either your account does not exist or is already activated.")
        
    except:
        return render_template('email-confirm.html',confirmation_msg="The link is invalid or has expired")    

@app.route("/email-confirm/")
def EmailConfirm():
    return render_template('email-confirm.html')

if __name__ == "__main__":
    #app.run()
    socketio.run(app)
    #wsgi.server(eventlet.listen(('', 8000)), app)