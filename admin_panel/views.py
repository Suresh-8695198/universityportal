from django.shortcuts import render, redirect
from firebase_admin import firestore, auth
from firebase.config import firebase_auth, db
from django.contrib import messages
from django.core.mail import send_mail
import random
import re
from django.utils.timezone import now
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import datetime
from django.core.files.storage import FileSystemStorage

from django.shortcuts import render, redirect
from django.http import HttpResponse
from .models import AdminOTP
from google.cloud import firestore
import re
import random
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from firebase_admin import firestore

# Change Password View
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth import update_session_auth_hash
from django.contrib import messages
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required


# Firestore instance
db = firestore.client()

# Admin Dashboard
def admin_dashboard(request):
    # Fetching total counts for departments, students, and staff
    departments = len(db.collection('departments').stream())
    students = len(db.collection('students').stream())
    staff = len(db.collection('staff').stream())

    # Fetching department list
    departments_list = db.collection('departments').stream()

    # Fetching student list
    students_list = db.collection('students').stream()

    # Fetching staff list
    staff_list = db.collection('staff').stream()

    # Fetching leaderboard data (students with coding statistics)
    leaderboard = db.collection('students').order_by('score').limit(10).stream()

    # Fetching recent staff posts
    recent_staff_posts = db.collection('staff').order_by('last_updated').limit(5).stream()

    context = {
        'departments': departments,
        'students': students,
        'staff': staff,
        'departments_list': departments_list,
        'students_list': students_list,
        'staff_list': staff_list,
        'leaderboard': leaderboard,
        'recent_staff_posts': recent_staff_posts
    }

    return render(request, 'admin_dashboard.html', context)

# Manage Departments
# Manage Departments
def manage_departments(request):
    if request.method == 'POST':
        department_name = request.POST.get('department_name')
        total_students = request.POST.get('total_students')
        year = request.POST.get('years')  # Now this will be a single value, not a list
        
        if department_name and total_students:
            db = firestore.client()
            # Save department data to Firestore, including year and total students
            db.collection('departments').add({
                'name': department_name,
                'year': year,  # Store the selected year as a string
                'total_students': int(total_students)  # Store total students as an integer
            })
            messages.success(request, f"Department '{department_name}' added successfully.")
            return redirect('manage_departments')
        else:
            messages.error(request, "Please provide all required fields.")

    # Fetch all departments from Firestore
    db = firestore.client()
    departments_ref = db.collection('departments').stream()

    # Prepare a list of department names, years, total students, and their document IDs
    departments_list = [{
        'id': department.id,
        'name': department.to_dict()['name'],
        'year': department.to_dict().get('year', 'N/A'),  # Now storing a single year
        'total_students': department.to_dict().get('total_students', 0)
    } for department in departments_ref]

    return render(request, 'manage_departments.html', {'departments_list': departments_list})


# Edit Department
def edit_department(request, dept_id):
    db = firestore.client()
    department_ref = db.collection('departments').document(dept_id)
    department = department_ref.get()
    if not department.exists:
        messages.error(request, "Department not found.")
        return redirect('manage_departments')

    if request.method == 'POST':
        department_name = request.POST.get('department_name')
        total_students = request.POST.get('total_students')
        years = request.POST.getlist('years')  # This will give you a list of selected years

        if department_name and total_students:
            department_ref.update({
                'name': department_name,
                'total_students': int(total_students),  # Update total students as integer
                'years': years
            })
            messages.success(request, f"Department '{department_name}' updated successfully.")
            return redirect('manage_departments')
        else:
            messages.error(request, "Please provide all required fields.")

    department_data = department.to_dict()
    return render(request, 'edit_department.html', {'department': department_data})

# Delete Department
def delete_department(request, dept_id):
    department_ref = db.collection('departments').document(dept_id)
    department_ref.delete()
    messages.success(request, "Department deleted successfully.")
    return redirect('manage_departments')

from django.http import Http404

def department_students(request, dept_id):
    try:
        department = Department.objects.get(id=dept_id)
    except Department.DoesNotExist:
        raise Http404("Department not found.")

    students = Student.objects.filter(department=department)

    if request.method == 'POST':
        roll_number = request.POST.get('roll_number')
        name = request.POST.get('name')
        dob = request.POST.get('dob')
        email = request.POST.get('email')
        contact = request.POST.get('contact')
        gender = request.POST.get('gender')
        age = request.POST.get('age')
        bench_id = request.POST.get('bench_id')

        # Add new student to the database
        new_student = Student.objects.create(
            roll_number=roll_number,
            name=name,
            dob=dob,
            email=email,
            contact=contact,
            gender=gender,
            age=age,
            department=department,
            bench_id=bench_id
        )
        return JsonResponse({'status': 'success'})

    return render(request, 'manage_students.html', {
        'department': department,
        'students': students,
    })
# Manage Students

def manage_students(request):
    # Fetching departments from Firestore
    departments_ref = db.collection('departments')
    departments_docs = departments_ref.stream()

    department_list = []
    for doc in departments_docs:
        dept_data = doc.to_dict()
        total_students = dept_data.get('total_students', 0)
        department_list.append({
            'id': doc.id,
            'name': dept_data.get('name', 'Unknown'),
            'total_students': total_students,
            'benches': list(range(1, total_students + 1)),  # 4 students per bench
            'years': dept_data.get('year', 'N/A')
        })

    if request.method == 'POST':
        try:
            # Retrieve data from POST request
            department_id = request.POST.get('department_id')
            bench_id = int(request.POST.get('bench_id'))
            roll_number = request.POST.get('roll_number')
            name = request.POST.get('name')
            dob = request.POST.get('dob')
            email = request.POST.get('email')
            contact = request.POST.get('contact')
            gender = request.POST.get('gender')
            age = int(request.POST.get('age'))

            # Validate department
            department_doc = db.collection('departments').document(department_id).get()
            if not department_doc.exists:
                return JsonResponse({'success': False, 'error': 'Department not found'})

            department_data = department_doc.to_dict()
            benches = list(range(1, ceil(department_data.get('total_students', 0) / 4) + 1))
            if bench_id not in benches:
                return JsonResponse({'success': False, 'error': 'Invalid bench ID'})

            # Add new student to Firestore
            student_data = {
                'roll_number': roll_number,
                'name': name,
                'dob': dob,
                'email': email,
                'contact': contact,
                'gender': gender,
                'age': age,
                'department_id': department_id,
                'bench_id': bench_id
            }
            db.collection('students').add(student_data)

            # Sending a success response
            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return render(request, 'manage_students.html', {'departments': department_list})
def add_student(request):
    try:
        # Get student data from the request
        student_data = request.POST
        roll_number = student_data.get('roll_number')

        # Check if the roll number already exists
        existing_student = db.collection('departments').document(department_id).collection('students').where('roll_number', '==', roll_number).stream()

        if any(existing_student):
            return JsonResponse({'success': False, 'message': 'Student with this roll number already exists.'}, status=400)

        # Add the new student to Firestore
        new_student_ref = db.collection('departments').document(department_id).collection('students').add(student_data)
        return JsonResponse({'success': True, 'message': 'Student added successfully', 'id': new_student_ref.id})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)



def view_departments(request):
    departments = []
    for dept in Department.objects.all():
        total_students = dept.students.count()  # Example
        benches_count = ceil(total_students / 4)  # 4 students per bench
        benches = list(range(1, benches_count + 1))
        departments.append({
            'id': dept.id,
            'name': dept.name,
            'total_students': total_students,
            'benches': benches,
        })
    return render(request, 'departments.html', {'departments': departments,'years':years})

def get_students_by_department(request):
    try:
        # Get department_id from the request
        department_id = request.GET.get('department_id')

        # Check if the department_id is provided
        if not department_id:
            return JsonResponse({'success': False, 'message': 'Department ID is required.'}, status=400)

        # Fetch students from the 'students' subcollection under the specified department
        dept_ref = db.collection('departments').document(department_id)
        students_ref = dept_ref.collection('students')
        students_docs = students_ref.stream()

        students_list = []
        for doc in students_docs:
            student_data = doc.to_dict()
            students_list.append({
                'id': doc.id,  # Firestore document ID
                'roll_number': student_data.get('roll_number'),
                'name': student_data.get('name'),
                'dob': student_data.get('dob'),
                'email': student_data.get('email'),
                'contact': student_data.get('contact'),
                'gender': student_data.get('gender'),
                'age': student_data.get('age')
            })

        # Return the student data as a JSON response
        return JsonResponse({'success': True, 'students': students_list})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

@csrf_exempt
def upload_excel(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        try:
            # Save the uploaded file
            excel_file = request.FILES['excel_file']
            fs = FileSystemStorage()
            filename = fs.save(excel_file.name, excel_file)
            file_path = fs.path(filename)
            
            # Read the Excel file
            df = pd.read_excel(file_path)
            
            # Get department ID from the POST data or default to 'MCA'
            department_id = request.POST.get('department_id', 'MCA')
            dept_ref = db.collection('departments').document(department_id).collection('students')

            # Track duplicate entries
            duplicate_entries = []
            added_entries = []

            # Process each row in the Excel sheet
            for index, row in df.iterrows():
                # Extract roll number
                roll_number = str(row['Roll_number'])

                # Check if a student with this roll number already exists
                existing_student = dept_ref.where('roll_number', '==', roll_number).stream()
                if any(existing_student):  # If student exists, skip and add to duplicates list
                    duplicate_entries.append(roll_number)
                    continue
                
                # Create a custom ID based on row index or roll number
                document_id = f"{index + 1:04d}"  # Sequential ID (e.g., 0001, 0002, etc.)
                
                # Ensure DOB is formatted as a string
                dob = row['DOB']
                if isinstance(dob, pd.Timestamp):  # If DOB is a pandas Timestamp, convert to string
                    dob = dob.strftime('%Y-%m-%d')  # Change format as needed (e.g., 'YYYY-MM-DD')
                elif isinstance(dob, datetime.datetime):  # If DOB is a datetime object
                    dob = dob.date().isoformat()  # Extract date and convert to ISO format

                # Prepare student data
                student_data = {
                    'roll_number': roll_number,
                    'name': row['Name'],
                    'dob': dob,  # Store as a string
                    'email': row['Email'],
                    'contact': str(row['Contact']),  # Convert to string to avoid issues
                    'gender': row['Gender'],
                    'age': int(row['Age']),
                    'year': row['Year'],
                }

                # Save to Firestore with custom ID
                dept_ref.document(document_id).set(student_data)
                added_entries.append(roll_number)
            
            # Clean up: Delete the uploaded file from storage
            fs.delete(filename)
            
            # Prepare response message
            response_message = {
                'success': True,
                'message': 'Students uploaded successfully.',
                'added_entries': added_entries,
                'duplicates': duplicate_entries
            }
            
            return JsonResponse(response_message)
        
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Invalid request or file missing.'}, status=400)

@csrf_exempt
def delete_all_students(request, department_id):
    if request.method == 'POST':
        try:
            # Validate the department_id
            if not department_id:
                return JsonResponse({'success': False, 'message': 'Department ID is required.'}, status=400)

            # Reference to the students collection under the specified department
            students_ref = db.collection('departments').document(department_id).collection('students')

            # Fetch all student documents in the collection
            students = students_ref.stream()

            # Delete each student document
            deleted_count = 0
            for student in students:
                student.reference.delete()
                deleted_count += 1

            return JsonResponse({'success': True, 'message': f'All students under department {department_id} deleted successfully.', 'deleted_count': deleted_count})

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    else:
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

#get Students
def get_students(request, dept_id):
    try:
        db = firestore.client()
        students_ref = db.collection('departments').document(dept_id).collection('students').stream()
        students = [
            {
                'roll_number': student.get('roll_number'),
                'name': student.get('name'),
            }
            for student in students_ref
        ]
        return JsonResponse({'success': True, 'students': students})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


# Edit Student
@csrf_exempt
def edit_student(request, student_id):
    student_ref = db.collection('students').document(student_id)
    student = student_ref.get()
    if not student.exists:
        return redirect('admin_dashboard')
    
    departments = db.collection('departments').stream()

    if request.method == 'POST':
        student_name = request.POST.get('name')
        department_id = request.POST.get('department')
        student_ref.update({'name': student_name, 'department': department_id})
        messages.success(request, f"Student '{student_name}' updated successfully.")
        return redirect('admin_dashboard')

    return render(request, 'edit_student.html', {'student': student.to_dict(), 'departments': departments})

# Delete Student
def delete_student(request, student_id):
    student_ref = db.collection('students').document(student_id)
    student_ref.delete()
    messages.success(request, f"Student deleted successfully.")
    return redirect('admin_dashboard')

# Manage Staff
def manage_staff(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        contact = request.POST.get('contact')
        if name and email and contact:
            db.collection('staff').add({'name': name, 'email': email, 'contact': contact})
            messages.success(request, f"Staff '{name}' added successfully.")
            return redirect('manage_staff')
        else:
            messages.error(request, "Please provide name, email, and contact.")
    
    staff_list = db.collection('staff').stream()
    return render(request, 'manage_staff.html', {'staff_list': staff_list})

#Get Staff
from django.http import JsonResponse
import logging

# Initialize logger
logger = logging.getLogger(__name__)

def get_staff(request):
    """Fetch all staff records from Firestore and return as JSON."""
    if request.method != "GET":
        return JsonResponse(
            {"success": False, "message": "Invalid request method"},
            status=405
        )

    try:
        # Fetch all staff documents from the 'staff' collection
        staff_collection = db.collection("staff").stream()
        staff_list = []

        for doc in staff_collection:
            data = doc.to_dict()
            data["id"] = doc.id
            staff_list.append(data)

        if not staff_list:
            return JsonResponse({"success": True, "staffs": [], "message": "No staff records found"}, status=200)

        return JsonResponse({"success": True, "staffs": staff_list}, status=200)
    
    except Exception as e:
        logger.error(f"Error fetching staff records: {e}")
        return JsonResponse({"success": False, "message": "Failed to fetch staff records"}, status=500)


from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.http import JsonResponse
import json  # for parsing the JSON request body

@csrf_exempt  # Temporarily disable CSRF protection (configure later)
@require_POST
def edit_staff(request, staff_id):
    try:
        print(f"Editing staff with ID: {staff_id}")  # Debug log

        # Fetch the JSON data from the request body
        data = json.loads(request.body)

        # Extract fields from the received JSON data
        name = data.get('name')
        email = data.get('email')
        contact = data.get('contact')

        # Validate data to make sure all fields are present
        if not name or not email or not contact:
            return JsonResponse({"success": False, "message": "All fields are required!"})

        # Fetch staff document from Firestore
        staff_ref = db.collection('staff').document(staff_id)
        staff = staff_ref.get()
        
        if not staff.exists:
            return JsonResponse({"success": False, "message": "Staff not found."})

        # Update the staff document in Firestore
        staff_ref.update({'name': name, 'email': email, 'contact': contact})
        
        return JsonResponse({"success": True, "message": "Staff updated successfully."})

    except Exception as e:
        return JsonResponse({"success": False, "message": f"Error: {str(e)}"})


def fetch_staff(request, staff_id):
    staff_ref = db.collection('staff').document(staff_id)
    staff = staff_ref.get()

    if staff.exists:
        staff_data = staff.to_dict()
        return JsonResponse({'success': True, 'staff': staff_data})
    else:
        return JsonResponse({'success': False, 'message': 'Staff not found.'})

# Delete Staff
@csrf_exempt  # This is for testing. Make sure to handle CSRF properly in production.
def delete_staff(request, staff_id):
    if request.method == 'DELETE':
        staff_ref = db.collection('staff').document(staff_id)
        try:
            staff_ref.delete()
            return JsonResponse({'success': True, 'message': 'Staff deleted successfully.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    else:
        return JsonResponse({'success': False, 'message': 'Invalid method'}, status=405)




import pandas as pd  # Ensure this line is present at the top of your file
import uuid

@csrf_exempt
def staff_upload_excel(request):
    if request.method == 'POST' and request.FILES.get('staff_excel_file'):  # Match form field name here
        try:
            # Save the uploaded file
            excel_file = request.FILES['staff_excel_file']  # Match form field name here
            fs = FileSystemStorage()
            filename = fs.save(excel_file.name, excel_file)
            file_path = fs.path(filename)
            
            # Read the Excel file
            df = pd.read_excel(file_path)
            print(f"Excel data: {df.head()}")  # Print first few rows of the Excel file for debugging

            # Reference to the 'staff' collection in Firestore
            dept_ref = db.collection('staff')

            # Track duplicate entries
            duplicate_entries = []
            added_entries = []

            # Process each row in the Excel sheet
            for index, row in df.iterrows():
                email = row['Email']
                print(f"Processing row {index + 1}: {email}")

                # Check if a staff member with this email already exists
                existing_staff = dept_ref.where('email', '==', email).stream()
                existing_staff_list = list(existing_staff)
                print(f"Existing staff for {email}: {existing_staff_list}")

                if existing_staff_list:
                    duplicate_entries.append(email)
                    continue
                
                # Create a custom ID (UUID for uniqueness)
                document_id = str(uuid.uuid4())  # Use UUID for unique document IDs

                # Prepare staff data
                staff_data = {
                    'name': row['Name'],
                    'email': row['Email'],
                    'contact': str(row['Contact']),
                }

                # Save to Firestore with custom ID
                dept_ref.document(document_id).set(staff_data)
                added_entries.append(email)
            
            # Clean up: Delete the uploaded file from storage
            fs.delete(filename)
            
            # Prepare response message
            response_message = {
                'success': True,
                'message': 'Staff uploaded successfully.',
                'added_entries': added_entries,
                'duplicates': duplicate_entries
            }
            
            return JsonResponse(response_message)
        
        except Exception as e:
            print(f"Error: {e}")  # Log any errors for debugging
            return JsonResponse({'success': False, 'message': f"Error: {str(e)}"}, status=500)
    
    return JsonResponse({'success': False, 'message': 'Invalid request or file missing.'}, status=400)

# Post News
def post_news(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        content = request.POST.get('content')
        if title and content:
            db.collection('news').add({'title': title, 'content': content, 'created_at': firestore.SERVER_TIMESTAMP})
            messages.success(request, "News posted successfully.")
            return redirect('admin_dashboard')
        else:
            messages.error(request, "Please provide a title and content for the news.")
    
    return render(request, 'post_news.html')

# Admin Forgot Password view
def admin_forgot_password(request):
    if request.method == 'POST':
        email = request.POST.get('email').strip().lower()
        
        try:
            # Check if user exists in Firestore admin_users collection
            admin_ref = db.collection('admin_users').where('email', '==', email).stream()
            admin_exists = any(admin_ref)

            if not admin_exists:
                return render(request, 'admin_forgot_password.html', {'error': 'No admin found with this email.'})
            
            # Generate and store OTP
            otp = random.randint(100000, 999999)
            AdminOTP.objects.update_or_create(email=email, defaults={'otp': otp, 'created_at': now()})

            # Send OTP via email
            send_otp_email(email, otp)
            return render(request, 'verify_otp.html', {'email': email})
        
        except Exception as e:
            print(f"Error during forgot password: {e}")
            return render(request, 'admin_forgot_password.html', {'error': 'Unexpected error occurred. Please try again.'})

    return render(request, 'admin_forgot_password.html')




def landing_page(request):
    return render(request, "landing_page.html")
from django.contrib.auth import authenticate, login
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from firebase_admin import firestore

def admin_login(request):
    if request.method == 'POST':
        email = request.POST.get('email').strip().lower()  # Normalize email input
        password = request.POST.get('password').strip()

        try:
            # Debugging: Log the attempt
            print(f"Attempting to find admin user with email: {email}")

            # Query Firestore for admin user by email
            admin_ref = firestore.client().collection('admin_users').where('email', '==', email).stream()
            admin_data = None
            for admin_doc in admin_ref:
                admin_data = admin_doc.to_dict()

            if admin_data:
                # Validate the password (you may want to hash the password for security)
                stored_password = admin_data.get('password')
                if stored_password == password:  # Simple password check (consider hashing passwords)
                    request.session['admin_id'] = email  # Set session for authenticated admin
                    return redirect('admin_dashboard')  # Redirect to dashboard after login
                else:
                    return render(request, 'admin_login.html', {'error': 'Invalid password'})

            else:
                return render(request, 'admin_login.html', {'error': 'Admin user not found'})

        except Exception as e:
            # Log the exception for debugging purposes
            print(f"Error occurred: {str(e)}")
            return render(request, 'admin_login.html', {'error': f'Error: {str(e)}'})

    return render(request, 'admin_login.html')  # For GET request, show the login page


@login_required
def admin_profile(request):
    try:
        admin_email = request.session.get('admin_id')

        if not admin_email:
            return redirect('admin_login')  # Redirect to login if no admin session

        # Fetch admin data from Firestore
        admin_ref = firestore.client().collection('admin_users').where('email', '==', admin_email).stream()
        admin_data = None
        for admin_doc in admin_ref:
            admin_data = admin_doc.to_dict()
        print(admin_data) 
        if admin_data:
            return render(request, 'admin_profile.html', {
                'admin_data': admin_data,
                'admin_email': admin_email  # Pass the email to the template to display it
            })
        else:
            return redirect('admin_login')  # Redirect if admin data is not found

    except Exception as e:
        # Log the exception for debugging purposes
        print(f"Error occurred: {str(e)}")
        return redirect('admin_login')  # Redirect to login on error



def logout(request):
   # This will log out the user
    return render(request, 'admin_login.html')  # Replace 'admin/login.html' with your actual login template

def admin_dashboard(request):
    # Fetch statistics from Firebase or database
    departments = 3
    students = 120
    staff = 15
    return render(request, 'admin_dashboard.html', {
        'departments': departments,
        'students': students,
        'staff': staff
    })




from django.utils.timezone import now

from .models import AdminOTP
import random
import re


def send_otp_email(email, otp):
    send_mail(
        'Password Reset OTP',
        f'Your OTP for resetting your admin password is: {otp}. It is valid for 10 minutes.',
        'suresh179073@gmail.com',  # Your sender email
        [email],
        fail_silently=False,
    )

# Admin Forgot Password view
def admin_forgot_password(request):
    """Handles admin password reset requests."""
    if request.method == 'POST':
        email = request.POST.get('email').strip().lower()  # Normalize email
        
        try:
            print(f"Checking for admin user with email: {email}")

            # Check if user exists in Firestore admin_users collection
            admin_ref = firestore.client().collection('admin_users').where('email', '==', email).stream()
            admin_exists = any(admin_ref)

            if not admin_exists:
                return render(request, 'admin_forgot_password.html', {'error': 'No admin found with this email.'})
            
            # Generate and store OTP
            otp = random.randint(100000, 999999)
            AdminOTP.objects.update_or_create(email=email, defaults={'otp': otp, 'created_at': now()})

            # Send OTP via email
            send_otp_email(email, otp)
            return render(request, 'verify_otp.html', {'email': email})
        
        except Exception as e:
            print(f"Error during forgot password: {e}")
            return render(request, 'admin_forgot_password.html', {'error': 'Unexpected error occurred. Please try again.'})

    return render(request, 'admin_forgot_password.html')


def verify_otp(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        entered_otp = request.POST.get('otp1') + request.POST.get('otp2') + request.POST.get('otp3') + request.POST.get('otp4') + request.POST.get('otp5') + request.POST.get('otp6')

        # Check if entered_otp is empty or None
        if not entered_otp:
            return render(request, 'verify_otp.html', {'error': 'OTP cannot be empty', 'email': email})

        try:
            otp_entry = AdminOTP.objects.get(email=email)

            # Check OTP expiration
            if otp_entry.is_expired():
                otp_entry.delete()
                return render(request, 'admin_forgot_password.html', {'error': 'OTP expired. Request a new one.'})

            # Verify OTP
            if otp_entry.otp == int(entered_otp):  # Ensure OTP is valid (and convert safely to integer)
                return render(request, 'reset_password.html', {'email': email})
            else:
                return render(request, 'verify_otp.html', {'error': 'Invalid OTP', 'email': email})

        except AdminOTP.DoesNotExist:
            return render(request, 'admin_forgot_password.html', {'error': 'No OTP found. Please request a new one.'})

        except ValueError:
            # Handle case where entered OTP is not a valid integer
            return render(request, 'verify_otp.html', {'error': 'Invalid OTP format. Please enter a valid number.', 'email': email})
def statistics(request):
    # Fetch student data from Firebase
    students_ref = db.collection('students')
    students_docs = students_ref.stream()

    # Process data
    total_students = 0
    total_problems_solved = 0
    active_students = 0
    leaderboard = []

    weekly_top = []
    monthly_top = []
    
    # Define date ranges
    today = datetime.datetime.now()
    one_week_ago = today - datetime.timedelta(days=7)
    one_month_ago = today - datetime.timedelta(days=30)

    for doc in students_docs:
        student = doc.to_dict()
        total_students += 1
        total_problems_solved += student.get('problems_solved', 0)

        if student.get('is_active', False):
            active_students += 1

        # Add to leaderboard
        leaderboard.append({
            "name": student.get('name', 'Unknown'),
            "problems_solved": student.get('problems_solved', 0)
        })

        # Weekly and Monthly Top Performers
        last_active = student.get('last_active', None)
        if last_active:
            last_active_date = datetime.datetime.fromisoformat(last_active)
            if last_active_date >= one_week_ago:
                weekly_top.append({
                    "name": student.get('name', 'Unknown'),
                    "problems_solved": student.get('problems_solved', 0)
                })
            if last_active_date >= one_month_ago:
                monthly_top.append({
                    "name": student.get('name', 'Unknown'),
                    "problems_solved": student.get('problems_solved', 0)
                })

    # Sort leaderboard, weekly_top, and monthly_top by problems solved
    leaderboard = sorted(leaderboard, key=lambda x: x['problems_solved'], reverse=True)[:10]
    weekly_top = sorted(weekly_top, key=lambda x: x['problems_solved'], reverse=True)[:5]
    monthly_top = sorted(monthly_top, key=lambda x: x['problems_solved'], reverse=True)[:5]

    # Context for the template
    context = {
        "total_students": total_students,
        "active_students": active_students,
        "total_problems_solved": total_problems_solved,
        "weekly_top": weekly_top,
        "monthly_top": monthly_top,
        "leaderboard": leaderboard,
    }

    return render(request, 'statistics.html', context)
            
from django.shortcuts import render

def admin_profile(request):
    # You can add context here, for example, admin details like name, email, etc.
    context = {
        'admin_name': 'Admin Name',  # Replace with actual data if needed
        'admin_email': 'admin@example.com',  # Replace with actual data if needed
    }
    return render(request, 'admin_profile.html', context)

    
def validate_password(password):
    
    if len(password) < 8:
        return "Password must be at least 8 characters."
    if not re.search(r'[A-Z]', password):
        return "Password must contain an uppercase letter."
    if not re.search(r'[a-z]', password):
        return "Password must contain a lowercase letter."
    if not re.search(r'[0-9]', password):
        return "Password must contain a digit."
    if not re.search(r'[!@#$%^&*]', password):
        return "Password must contain a special character."
    return None



def reset_password(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        new_password = request.POST.get('password')

        # Validate password
        password_error = validate_password(new_password)
        if password_error:
            return render(request, 'reset_password.html', {'error': password_error, 'email': email})

        try:
            # Step 1: Update Firestore password
            db = firestore.client()
            admin_ref = db.collection('admin_users').where('email', '==', email).stream()
            
            # Find the admin document
            admin_data = None
            for doc in admin_ref:
                admin_data = doc.to_dict()

            if admin_data:
                # Update the password in Firestore
                admin_ref = db.collection('admin_users').document(doc.id)
                admin_ref.update({'password': new_password})

                # Step 2: Clear OTP from the AdminOTP table
                AdminOTP.objects.filter(email=email).delete()

                return redirect('admin_login')  # Redirect to login page
            else:
                return render(request, 'reset_password.html', {'error': 'Admin user not found', 'email': email})

        except Exception as e:
            return render(request, 'reset_password.html', {'error': f'Error: {e}', 'email': email})









# Change Password View
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()  # Save the new password
            update_session_auth_hash(request, form.user)  # Keep the user logged in
            messages.success(request, 'Your password has been successfully updated.')
            return redirect('login')  # Redirect to the login page after successful password change
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(user=request.user)

    return render(request, 'change_password.html', {'form': form})
'''
from django.shortcuts import render, redirect
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login

def custom_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('home')  # Redirect to a page after login, e.g., homepage
    else:
        form = AuthenticationForm()
    
    return render(request, 'login.html', {'form': form})
'''