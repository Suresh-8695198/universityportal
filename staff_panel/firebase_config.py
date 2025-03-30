import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase admin app for the 'admin' database
try:
    admin_app = firebase_admin.get_app('admin')  # Check if 'admin' app already exists
except ValueError:
    admin_cred = credentials.Certificate('staff_panel\\firebase\\admin_portal.json')
    admin_app = firebase_admin.initialize_app(admin_cred, name='admin')

# Initialize Firebase admin app for the 'staff' database
try:
    staff_app = firebase_admin.get_app('staff')  # Check if 'staff' app already exists
except ValueError:
    staff_cred = credentials.Certificate('staff_panel\\firebase\\staff_portal.json')
    staff_app = firebase_admin.initialize_app(staff_cred, name='staff')

# Access Firestore databases
admin_db = firestore.client(admin_app)  # Admin database instance
staff_db = firestore.client(staff_app)  # Staff database instance
