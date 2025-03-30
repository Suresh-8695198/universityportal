import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase admin app for the 'admin' database
try:
    admin_app = firebase_admin.get_app('admin')  # Check if 'admin' app already exists
except ValueError:
    admin_cred = credentials.Certificate('student_portal\\firebase\\admin_portal.json')
    admin_app = firebase_admin.initialize_app(admin_cred, name='admin')

# Initialize Firebase admin app for the 'staff' database
try:
    staff_app = firebase_admin.get_app('staff')  # Check if 'staff' app already exists
except ValueError:
    staff_cred = credentials.Certificate('student_portal\\firebase\\staff_portal.json')
    staff_app = firebase_admin.initialize_app(staff_cred, name='staff')

# Initialize Firebase admin app for the 'students' database
try:
    students_app = firebase_admin.get_app('students')  # Check if 'students' app already exists
except ValueError:
    students_cred = credentials.Certificate('student_portal\\firebase\\students_portal.json')
    students_app = firebase_admin.initialize_app(students_cred, name='students')

# Access Firestore clients
admin_db = firestore.client(app=admin_app)
staff_db = firestore.client(app=staff_app)
students_db = firestore.client(app=students_app)
