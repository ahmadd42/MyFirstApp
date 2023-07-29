"""Flask configuration."""

#Main Config
TESTING = True
DEBUG = False
#FLASK_ENV = 'development'
SECRET_KEY = 'Sit@rA_gOlD'
SECURITY_PASSWORD_SALT = 'Sit@rA_gOlD_p285f'
SESSION_PERMANENT = False
SESSION_TYPE = "filesystem"

#MySQL database configuration
MYSQL_HOST = 'localhost'
MYSQL_USER = 'root'
MYSQL_PASSWORD = 'Ask@ri123'
MYSQL_DB = "ChatterBox"

#App password for gmail account
MAIL_SENDER = 'ahmadd42@gmail.com'
MAIL_APP_PASSWORD = 'tyrhysfknxnxfbew'