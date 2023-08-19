from datetime import date
import datetime
import json
import signal
from flask import Flask, render_template, request
from .tables import db, CodeTable, Registration, TodayDate
from config import database_config, default_wifi_password
from waitress import serve

class WebServer:

    def __init__(self, on_success_callback=None):
        self.app = Flask(__name__)
        self.on_success_callback = on_success_callback
        self.default_code_duration = 60
        self.server = None

        # database configuration
        self.app.config['SQLALCHEMY_DATABASE_URI'] = database_config
        self.app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        self.db = db
        self.db.init_app(self.app)

        # save the database
        with self.app.app_context():
            self.db.create_all()
            db.session.commit()



        # Routes and views
        @self.app.route('/')
        def index():
            return render_template('index.html')
        

        @self.app.route('/submit', methods=['POST'])
        def submit_form():
            # check if the code from the form is not empty and sanitize it
            code = request.form.get('code', '').strip().upper()

            # validate the code
            if not code:
                error = 'No code provided!'
            elif not (code.isalnum() and len(code) == 11):
                error = 'Invalid code provided!'
            else:
                error = None

            if error:
                return render_template('index.html', error=error)

            # check if the code exists in the code table
            code_obj = CodeTable.query.filter_by(code=code).first()
            if code_obj:
                code_obj.used = True
                self.db.session.commit()
                duration = code_obj.time
                # grab the IP address of the user
                ip = request.remote_addr

                # add the IP address and code to the Registration table
                device_entry = Registration.query.filter_by(ip_address=ip).first()
                if device_entry:
                    device_entry.code = code
                else:
                    registration = Registration(ip_address=ip, code=code)
                    self.db.session.add(registration)

                try:
                    self.db.session.commit()
                    if self.on_success_callback:
                        self.on_success_callback((ip, code, duration))  # Call the callback function 
                except Exception as e:
                    print(f"Error committing changes to database: {e}")
                    self.db.session.rollback()

                return render_template('success.html')
            else:
                error = f'Code {code} is invalid!'

            return render_template('index.html', error=error)

       

    def add_code(self, code, time=None):
        with self.app.app_context():
            code_obj = CodeTable.query.filter_by(code=code).first()
            if code_obj:
                print(f"Code {code} already exists in the database.")
            else:
                code_obj = CodeTable(code=code)
                code_obj.used = False
                # if no time is provided, use the default time
                code_obj.time = self.default_code_duration if time is None else time
                db.session.add(code_obj)
                try:
                    db.session.commit()
                    print(f"Code {code} added to the database.")
                    return True
                except Exception as e:
                    print(f"Error committing changes to database: {e}")
                    db.session.rollback()   
                    return False

    def get_all_registration(self):
        with self.app.app_context():
            try:
                devices = Registration.query.all()
                device_list = []
                for d in devices:
                    mac = d.mac
                    code = d.code
                    device_list.append((mac, code))
                return device_list
            except Exception as e:
                print(f"Error querying database to get all registrations: {e}")
                return []
            
    # query the database for all codes and return them
    def get_all_codes(self):
        with self.app.app_context():
            try:
                codes = CodeTable.query.all()
                code_list = []
                for c in codes:
                    code = c.code
                    duration = c.time
                    status = "Used" if c.used else "Unused"
                    code_list.append((code, status, duration))
                return code_list
            except Exception as e:
                print(f"Error querying database to get all codes: {e}")
                return []
            
    def update_code(self, code, time):
        with self.app.app_context():
            code_obj = CodeTable.query.filter_by(code=code).first()
            if code_obj:
                code_obj.time = time
                try:
                    db.session.commit()
                    print(f"Code: {code} Time: {code_obj.time} updated in the database.")
                except Exception as e:
                    print(f"Error updating code {code} in the database: {e}")
                    db.session.rollback()
            else:
                print(f"Code {code} does not exist in the database.")

    def update_registration(self, ip, mac):
        with self.app.app_context():
            device_entry = Registration.query.filter_by(ip_address=ip).first()
            if device_entry:
                device_entry.mac = mac
                try:
                    db.session.commit()
                    print(f"IP: {ip} MAC: {mac} updated in the database.")
                except Exception as e:
                    print(f"Error updating IP {ip} in the database: {e}")
                    db.session.rollback()
            else:
                print(f"IP {ip} does not exist in the database.")
   
    def delete_code(self, code):
        with self.app.app_context():
            code_obj = CodeTable.query.filter_by(code=code).first()
            if code_obj:
                try:
                    db.session.delete(code_obj)
                    db.session.commit()
                    print(f"Code {code} deleted from the database.")
                except Exception as e:
                    print(f"Error deleting code {code} in the database: {e}")
                    db.session.rollback()
            else:
                print(f"Code {code} does not exist in the database.")

    def delete_expired_codes(self, expired_codes):
        with self.app.app_context():
            for code in expired_codes:
                code_obj = CodeTable.query.filter_by(code=code).first()
                if code_obj:
                    try:
                        self.db.session.delete(code_obj)
                        self.db.session.commit()
                    except Exception as e:
                        print(f"Error deleting code {code} in the database: {e}")
                        self.db.session.rollback()


    def reset_database(self):
        with self.app.app_context():
            db.session.query(CodeTable).delete()
            # db.session.query(Registration).delete()
            db.session.commit()
            print("Database reset.")
    

    def is_new_day(self):
        with self.app.app_context():
            today_date = date.today().strftime('%Y-%m-%d')
            last_date = TodayDate.query.first()
            try:
                if last_date is not None:
                    # if the last date in the database is not today's date, update the database and return True
                    if last_date.date != today_date:
                        last_date.date = today_date
                        db.session.commit()
                        return True
                    else:
                        # if the last date in the database is today's date, return False
                        return False
                else:
                    # if there are no dates in the table, add today's date to the database and return True
                    today_date_obj = TodayDate(date=today_date)
                    today_date_obj.router_password = default_wifi_password
                    db.session.add(today_date_obj)
                    db.session.commit()
                    return True
            except Exception as e:
                print(f"Error updating date: {e}")
                db.session.rollback()
                return False
            

    def change_router_password(self, new_password):
        with self.app.app_context():
            last_date = TodayDate.query.first()
            try:
                last_date.router_password = new_password
                db.session.commit()
            except Exception as e:
                print(f"Error updating router password: {e}")
                db.session.rollback()

    def get_router_password(self):
        with self.app.app_context():
            last_date = TodayDate.query.first()
            return last_date.router_password

    def run(self):
        self.server = serve(self.app, host='192.168.0.157', port=80)
        # Add a signal handler for SIGTERM (termination signal)
        signal.signal(signal.SIGTERM, self.shutdown)
        # Start the server
        try:
            self.server.run()
        except KeyboardInterrupt:
            pass

    def shutdown(self):
        # Close the database connection
        with self.app.app_context():
            self.db.session.remove()
        print("Server shut down.")