from django.shortcuts import render, redirect

from django.contrib.auth import logout as auth_logout
from firebase_admin import firestore
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .firebase_config import admin_db, staff_db
from django.http import JsonResponse
import json

from django.contrib.auth.decorators import login_required


@csrf_exempt
def staff_login(request):
    if request.method == 'GET':
        return render(request, 'staff_login.html')  # Render the login page

    elif request.method == 'POST':
        try:
            # Parse the POST request data (assuming JSON format)
            data = json.loads(request.body)
            email = data.get('email')
            contact = data.get('contact')

            print(f"Email: {email}, Contact: {contact}")

            # Fetch staff record from Firestore (admin_db)
            staff_ref = admin_db.collection('staff')\
                .where('email', '==', email)\
                .where('contact', '==', contact)\
                .stream()

            staff_list = [staff.to_dict() for staff in staff_ref]

            if staff_list:
                # Staff found - successful login
                staff = staff_list[0]

                # Store staff email and authentication status in session
                request.session['staff_id'] = staff.get('email')
                request.session['is_authenticated'] = True

                # Save or update staff profile in staff_db
                staff_email = staff.get('email')
                staff_doc_ref = staff_db.collection('staff_profiles').document(staff_email)

                # Define the profile data
                profile_data = {
                    'email': staff_email,
                    'name': staff.get('name', 'Unknown Name'),
                    'contact': staff.get('contact', 'Unknown Contact'),
                    'profile_picture': staff.get('profile_picture', ''),  # Default profile picture if not set
                    'news_posts': staff.get('news_posts', []),  # Preserve existing data if available
                    'notes': staff.get('notes', [])  # Preserve existing data if available
                }

                # Check if the profile already exists
                if staff_doc_ref.get().exists:
                    print(f"Profile for {staff_email} already exists. Updating missing fields...")
                    staff_doc_ref.set(profile_data, merge=True)
                else:
                    print(f"Creating new profile for {staff_email}...")
                    staff_doc_ref.set(profile_data)

                return JsonResponse({'message': 'Login successful', 'redirect': '/staff/dashboard/'})
            else:
                # Staff not found
                return JsonResponse({'error': 'Invalid credentials or staff not found'}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON format'}, status=400)
        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({'error': 'An error occurred during login'}, status=500)

    return JsonResponse({'error': 'Invalid request method'}, status=405)


from django.http import JsonResponse

def staff_dashboard(request):
    staff_email = request.session.get('staff_id')
    try:
        departments_ref = admin_db.collection('departments').stream()
        departments = [dept.id for dept in departments_ref]
        department_students = {}

        staff_doc_ref = staff_db.collection('staff_profiles').document(staff_email)
        staff_profile = staff_doc_ref.get().to_dict()

        for department_id in departments:
            students_ref = admin_db.collection('departments').document(department_id).collection('students').stream()
            students = [student.to_dict() for student in students_ref]
            
            if students:
                department_students[department_id] = students
        
        context = {
            'departments': departments,
            'department_students': department_students,
             'show_widgets': True, 
             "staff": staff_profile,
             
        }
      
        return render(request, 'staff_dashboard.html', context)
    except Exception as e:
        return JsonResponse({'error': 'An error occurred while fetching data', 'details': str(e)}, status=500)


from django.shortcuts import render

# Create your views here.
def home(request):
    return render(request, 'home.html')



#Profile Page
@login_required(login_url='/staff/login/')
def staff_profile(request):
    # Get logged-in staff email from session
    staff_email = request.session.get('staff_id')
    if not staff_email:
        return redirect('/staff/login/')

    # Fetch staff profile from Firestore
    staff_doc_ref = staff_db.collection('staff_profiles').document(staff_email)
    staff_profile = staff_doc_ref.get().to_dict()

    if not staff_profile:
        return render(request, "profile.html", {"error": "Profile not found."})

    if request.method == "POST":
        # Update basic information
        new_name = request.POST.get('name')
        new_contact = request.POST.get('contact')
        profile_picture = request.FILES.get('profile_picture')

        # Prepare data to update
        update_data = {}
        if new_name:
            update_data["name"] = new_name
        if new_contact:
            update_data["contact"] = new_contact

        # Handle profile picture upload (optional)
        if profile_picture:
            # Assuming Firebase Storage is configured
            bucket = firebase_admin.storage.bucket()
            blob = bucket.blob(f"profile_pictures/{staff_email}")
            blob.upload_from_file(profile_picture)
            update_data["profile_picture"] = blob.public_url

        # Update Firestore document
        if update_data:
            staff_doc_ref.update(update_data)

        return redirect('/staff/profile/')

    return render(request, "profile.html", {"profile": staff_profile, 'show_widgets': False})


# Get Students in a Department
def get_students_by_department(request):
    try:
        # Get department_id from the request
        department_id = request.GET.get('department_id')

        if not department_id:
            return JsonResponse({'success': False, 'message': 'Department ID is required.'}, status=400)

        # Fetch students from the Firestore collection under the specified department
        students_ref = admin_db.collection('departments').document(department_id).collection('students')
        students_docs = students_ref.stream()

        students_list = []
        for doc in students_docs:
            student_data = doc.to_dict()
            students_list.append({
                'id': doc.id,
                'roll_number': student_data.get('roll_number'),
                'name': student_data.get('name'),
            })

        return JsonResponse({'success': True, 'students': students_list})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

# Post Assignment to a Department
def post_assignment(request):
    if request.method == 'POST':
        try:
            department_id = request.POST.get('department_id')
            title = request.POST.get('title')
            description = request.POST.get('description')
            deadline = request.POST.get('deadline')

            if not department_id or not title or not description or not deadline:
                return JsonResponse({'success': False, 'message': 'All fields are required.'}, status=400)

            # Get the department document reference
            dept_ref = admin_db.collection('departments').document(department_id)

            # Add the assignment to the 'assignments' subcollection under the department
            assignments_ref = dept_ref.collection('assignments')
            assignments_ref.add({
                'title': title,
                'description': description,
                'deadline': deadline,
                'posted_at': firestore.SERVER_TIMESTAMP
            })

            return JsonResponse({'success': True, 'message': 'Assignment posted successfully.'})

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)
    else:
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=400)

# Fetch Departments and Render to Template
def view_departments(request):
    try:
        departments_ref = admin_db.collection('departments')
        departments_docs = departments_ref.stream()

        departments = []
        for dept in departments_docs:
            dept_data = dept.to_dict()
            departments.append({
                'id': dept.id,
                'name': dept_data.get('name')
            })

        return render(request, 'assignments.html', {'departments': departments})

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

# View for displaying the assignments page
def assignments_page(request):
    try:
        # Fetch departments from the 'departments' collection
        departments_ref = admin_db.collection('departments')
        departments_docs = departments_ref.stream()

        departments = []

        # Loop through each department document
        for dept in departments_docs:
            dept_data = dept.to_dict()

            # Get the total number of students and years from the department document
            total_students = dept_data.get('total_students', 0)  # Directly get the total students field
            years = dept_data.get('year', [])  # Get years from the department document (assumed to be a list)

            departments.append({
                'id': dept.id,
                'name': dept_data.get('name', 'N/A'),
                'total_students':  len(list(dept.reference.collection('students').stream())),
                'years': years,  # Assuming 'years' is a list or string
            })

        # Pass the data to the template
        return render(request, 'assignments.html', {'departments': departments})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

#get Students
def view_department(request, dept_id):
    try:
        # Fetch department data
        dept_ref = admin_db.collection('departments').document(dept_id)
        dept_data = dept_ref.get().to_dict()

        if not dept_data:
            return JsonResponse({'success': False, 'message': 'Department not found'}, status=404)

        # Fetch students for this department
        students_ref = dept_ref.collection('students')
        students_docs = students_ref.stream()

        students = []
        for student in students_docs:
            student_data = student.to_dict()
            students.append({
                'id': student.id,
                'name': student_data.get('name', 'N/A'),
                'roll_number': student_data.get('roll_number', 'N/A'),
                'email': student_data.get('email', 'N/A')
            })

        # Fetch assignments for the department
        assignments_ref = dept_ref.collection('assignments')
        assignments_docs = assignments_ref.stream()

        assignments = []
        for assignment in assignments_docs:
            assignment_data = assignment.to_dict()
            assignments.append({
                'id': assignment.id,
                'title': assignment_data.get('title', 'Untitled'),
                'description': assignment_data.get('description', 'No description'),
                'deadline': assignment_data.get('deadline', 'No deadline')
            })

        # If no assignments are found, return a default message
        if not assignments:
            assignments = [{
                'id': None,
                'title': 'No assignments available',
                'description': 'There are no assignments posted yet.',
                'deadline': 'N/A'
            }]

        # Pass the data to the template
        return render(request, 'department_detail.html', {
            'department': dept_data,
            'students': students,
            'dept_id': dept_id,  
            'assignments': assignments
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


#Post Assignments
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect

from datetime import datetime  # Import datetime module
from django.views.decorators.csrf import csrf_exempt
@csrf_exempt

def post_assignment(request, dept_id):
    if request.method == 'POST':
        # Ensure data is received as JSON
        try:
            title = request.POST.get('title')
            description = request.POST.get('description')
            deadline = request.POST.get('deadline')

            # Check if all fields are provided
            if not title or not description or not deadline:
                return JsonResponse({'success': False, 'message': 'All fields are required'}, status=400)

            # Convert the deadline string to a datetime object
            try:
                deadline = datetime.strptime(deadline, "%Y-%m-%dT%H:%M")
            except ValueError:
                return JsonResponse({'success': False, 'message': 'Invalid deadline format'}, status=400)

            # Fetch the department and create the assignment
            dept_ref = admin_db.collection('departments').document(dept_id)
            dept_data = dept_ref.get().to_dict()

            if not dept_data:
                return JsonResponse({'success': False, 'message': 'Department not found'}, status=404)

            # Create the assignment
            assignments_ref = dept_ref.collection('assignments')
            assignments_ref.add({
                'title': title,
                'description': description,
                'deadline': deadline,
                'created_at': datetime.now()
            })

            return JsonResponse({'success': True, 'message': 'Assignment posted successfully'})

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)


'''

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import json

@csrf_exempt
def post_quiz(request, dept_id):
    if request.method == 'POST':
        try:
            # Parse JSON body
            body = json.loads(request.body.decode('utf-8'))
            
            # Extract data
            title = body.get('title')
            description = body.get('description')
            deadline = body.get('deadline')
            questions = body.get('questions')
            
            # Validate required fields
            if not all([title, description, deadline, questions]):
                return JsonResponse({'success': False, 'message': 'All fields are required'}, status=400)
            
            # Validate deadline format
            try:
                deadline = datetime.strptime(deadline, "%Y-%m-%dT%H:%M")
            except ValueError:
                return JsonResponse({'success': False, 'message': 'Invalid deadline format'}, status=400)
            
            # Validate questions
            if not isinstance(questions, list) or len(questions) == 0:
                return JsonResponse({'success': False, 'message': 'Questions must be a non-empty list'}, status=400)
            
            for question in questions:
                if not all(key in question for key in ['question', 'options', 'correct_answer']):
                    return JsonResponse({'success': False, 'message': 'Each question must have "question", "options", and "correct_answer".'}, status=400)
                if not isinstance(question['options'], list) or len(question['options']) < 2:
                    return JsonResponse({'success': False, 'message': 'Each question must have at least two options.'}, status=400)
            
            # Reference department and add quiz
            dept_ref = admin_db.collection('departments').document(dept_id)
            if not dept_ref.get().exists:
                return JsonResponse({'success': False, 'message': 'Department not found'}, status=404)
            
            quizzes_ref = dept_ref.collection('quizzes')
            quizzes_ref.add({
                'title': title,
                'description': description,
                'deadline': deadline,
                'questions': questions,
                'created_at': datetime.now()
            })
            
            return JsonResponse({'success': True, 'message': 'Quiz posted successfully'})
        
        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Invalid JSON format'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'success': False, 'message': 'Invalid request method'}, status=405)
'''
from django.shortcuts import render
from django.http import JsonResponse, FileResponse
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
import io
import os

import datetime


# Path to your service account JSON file
SERVICE_ACCOUNT_FILE = "staff_panel/google-drive.json"  # Correct the path to your service account file

# Authenticate using the service account
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE,
    scopes=["https://www.googleapis.com/auth/drive"]
)

# Build the Drive service
drive_service = build("drive", "v3", credentials=credentials)

from googleapiclient.errors import HttpError

# Folder ID in Google Drive where files will be uploaded
DRIVE_FOLDER_ID = "1PpkH1_7_Sz8mpetPCUir8XrsAJib4pAT"  # Replace with your root folder ID
import logging

# Initialize logger
logger = logging.getLogger(__name__)

def upload_to_drive(request, dept_id, class_name):
    try:
        # Fetch department data
        dept_ref = admin_db.collection('departments').document(dept_id)
        dept_data = dept_ref.get().to_dict()
        if not dept_data:
            logger.error(f"Department with ID {dept_id} not found.")
            return JsonResponse({"success": False, "message": "Department not found"}, status=404)

        department_name = dept_data.get('name', 'N/A')

        # Create folder for the department if it doesn't exist
        parent_folder_id = DRIVE_FOLDER_ID  # Root folder for all departments
        department_folder_id = create_drive_folder(department_name, parent_folder_id)

        # Create a subfolder for the class (e.g., I-MCA, II-MCA)
        class_folder_id = create_drive_folder(f"{class_name}-{department_name}", department_folder_id)

        if request.method == 'POST' and request.FILES.get('file'):
            title = request.POST.get('title', '').strip()
            if not title:
                logger.error(f"Title is missing in POST request.")
                return JsonResponse({"success": False, "message": "Title is required"}, status=400)

            file = request.FILES['file']

            file_name = file.name

            # Upload the file to Google Drive in the class folder
            file_metadata = {
                "name": file_name,
                "parents": [class_folder_id]
            }

            file_content = io.BytesIO(file.read())
            media = MediaIoBaseUpload(file_content, mimetype=file.content_type, resumable=True)

            uploaded_file = drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields="id, webViewLink, webContentLink, mimeType"
            ).execute()

            file_id = uploaded_file.get("id")
            drive_service.permissions().create(
                fileId=file_id,
                body={'role': 'reader', 'type': 'anyone'}
            ).execute()

            file_url = uploaded_file.get("webViewLink")

            # Store the file metadata in Firestore under the department's "notes" collection
            note_data = {
                'title': title,
                'file_name': file_name,
                'file_url': file_url,
                'file_id': file_id,
                'class_name': class_name,
                'uploaded_at': datetime.datetime.utcnow()
            }
            notes_ref = dept_ref.collection('notes')
            notes_ref.add(note_data)

            return JsonResponse({
                "success": True,
                "file_url": file_url,
                "file_id": file_id,
                "file_name": file_name,
                "title": title,
                "message": "File uploaded successfully"
            })

        if request.method == 'GET' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            files = list_files_in_folder(class_folder_id, dept_id)
            return JsonResponse({"success": True, "files": files})

        # Render the page for non-AJAX requests
        files = list_files_in_folder(class_folder_id, dept_id)
        return render(request, 'upload_to_drive.html', {
            'dept_id': dept_id,
            'class_name': class_name,
            'files': files,
        })

    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({"success": False, "message": str(e)}, status=500)
        return render(request, 'upload_to_drive.html', {
            'error_message': str(e),
            'dept_id': dept_id,
            'class_name': class_name,
        })

import logging

# Setup logger
logger = logging.getLogger(__name__)

def list_files_in_folder(folder_id, dept_id):
    try:
        query = drive_service.files().list(
            q=f"'{folder_id}' in parents and trashed=false",
            fields="files(id, name, mimeType, size, webViewLink)"
        ).execute()

        files = query.get('files', [])

        if not files:
            logger.warning(f"No files found in folder {folder_id}")
            return []

        # Process files and fetch titles
        unique_files = {}
        for file in files:
            file_id = file.get('id')
            if not file_id:
                logger.warning("Skipping file with missing ID")
                continue

            unique_files[file_id] = {
                'name': file.get('name', 'Unnamed File'),
                'size': file.get('size', 0),
                'webViewLink': file.get('webViewLink', ''),
            }

        dept_ref = admin_db.collection('departments').document(dept_id)

        for file_id, file_data in unique_files.items():
            try:
                note_ref = dept_ref.collection('notes').where('file_id', '==', file_id).limit(1).get()

                if note_ref:
                    note_data = note_ref[0].to_dict()
                    file_data['title'] = note_data.get('title', 'No title available')
                else:
                    file_data['title'] = 'No title available'

            except Exception as e:
                logger.error(f"Error fetching note for file_id {file_id}: {str(e)}")
                file_data['title'] = 'Error fetching title'

        return list(unique_files.values())

    except Exception as e:
        logger.error(f"Error fetching files: {str(e)}")
        return []



def create_drive_folder(folder_name, parent_folder_id):
    try:
        # Check if the folder already exists
        query = f"'{parent_folder_id}' in parents and name = '{folder_name}' and mimeType = 'application/vnd.google-apps.folder'"
        results = drive_service.files().list(q=query, fields="files(id)").execute()
        existing_folders = results.get('files', [])

        if existing_folders:
            return existing_folders[0]['id']  # Return the existing folder ID
        else:
            # Create the folder if it doesn't exist
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_folder_id]
            }
            folder = drive_service.files().create(body=file_metadata, fields='id').execute()
            return folder.get('id')

    except Exception as e:
        print(f"Error creating folder {folder_name}: {str(e)}")
        return None


'''
def view_uploaded_files(request):
    try:
        # List all files in the specified folder
        query = f"'{DRIVE_FOLDER_ID}' in parents" if DRIVE_FOLDER_ID else "trashed = false"
        results = drive_service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        files = results.get('files', [])
        print("Files in folder:", files)  # Print files for debugging

        return render(request, 'view_uploaded_files.html', {'files': files})

    except Exception as e:
        print("Error:", e)  # Print error for debugging
        return JsonResponse({"success": False, "message": str(e)}, status=500)
'''
def delete_from_drive(request, file_id, dept_id, class_name):
    if request.method == 'POST':
        try:
            # Delete the file from Google Drive
            drive_service.files().delete(fileId=file_id).execute()

            # Remove the file entry from Firestore
            dept_ref = admin_db.collection('departments').document(dept_id)
            notes_ref = dept_ref.collection('notes')

            all_docs = notes_ref.stream()
            for doc in all_docs:
                print(f"Document ID: {doc.id}, Data: {doc.to_dict()}")


            # Query the notes collection using file_id
            query = notes_ref.where('file_id', '==', file_id).get()

            if not query:
                print("No matching document found in Firestore.")


            # Delete the matching document
            for doc in query:
                print(f"Deleting document: {doc.id}")
                doc.reference.delete()


            # Redirect to refresh the files list
            return redirect('upload_to_drive', dept_id=dept_id, class_name=class_name)

        except HttpError as error:
            return render(request, 'upload_to_drive.html', {
                'dept_id': dept_id,
                'class_name': class_name,
                'error_message': f"Error deleting file: {error}",
            })
        except Exception as e:
            return render(request, 'upload_to_drive.html', {
                'dept_id': dept_id,
                'class_name': class_name,
                'error_message': str(e),
            })
    else:
        return redirect('upload_to_drive', dept_id=dept_id, class_name=class_name)



def preview_pdf(request, file_id):
    try:
        # Construct the Google Drive viewer URL
        google_drive_url = f"https://drive.google.com/file/d/{file_id}/preview"

        return render(request, 'preview_pdf.html', {'google_drive_url': google_drive_url})

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)

def download_from_drive(request, file_id):
    try:
        # Fetch the file metadata
        request = drive_service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        # Return the file as a response
        fh.seek(0)
        return FileResponse(fh, as_attachment=True, filename="downloaded_file")

    except Exception as e:
        return JsonResponse({"success": False, "message": str(e)}, status=500)




#View Notes
def post_notes_page(request):
    try:
        # Fetch departments from the 'departments' collection
        departments_ref = admin_db.collection('departments')
        departments_docs = departments_ref.stream()

        departments = []

        # Loop through each department document
        for dept in departments_docs:
            dept_data = dept.to_dict()

            # Get the department name
            department_name = dept_data.get('name', 'N/A')

            total_students = dept_data.get('total_students', 0) 

            # If 'year' is stored as a single value (e.g., "II"), convert it into a list for consistency
            years = dept_data.get('years', []) if isinstance(dept_data.get('years', []), list) else [dept_data.get('years', '')]

            departments.append({
                'id': dept.id,
                'name': department_name,
                'total_students': total_students,
                'years': dept_data.get('year', []),   # Use the years list (even if it's a single entry)
            })

        # Pass the data to the template
        return render(request, 'post_notes.html', {'departments': departments})
    
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

# View to display students and allow posting notes
def list_department(request, dept_id):
    try:
        # Fetch department data
        dept_ref = admin_db.collection('departments').document(dept_id)
        dept_data = dept_ref.get().to_dict()

        if not dept_data:
            return JsonResponse({'success': False, 'message': 'Department not found'}, status=404)

        # Fetch students for this department
        students_ref = dept_ref.collection('students')
        students_docs = students_ref.stream()

        students = []
        for student in students_docs:
            student_data = student.to_dict()
            students.append({
                'id': student.id,
                'name': student_data.get('name', 'N/A'),
                'roll_number': student_data.get('roll_number', 'N/A'),
                'email': student_data.get('email', 'N/A')
            })

        # Pass the data to the template, including the years (classes)
        return render(request, 'department_students.html', {
            'department': dept_data,
            'students': students,
            'dept_id': dept_id,
            'years': dept_data.get('year', []),  # Pass the list of classes (years)
        })

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

#Post News and Annoucements
# View to display all departments
def show_departments(request):
    try:
        # Fetch departments from Firebase
        departments_ref = admin_db.collection('departments')
        departments = []
        for dept in departments_ref.stream():
            dept_data = dept.to_dict()
            departments.append({
                'id': dept.id,
                'name': dept_data.get('name', 'N/A'),
                'total_students': len(list(dept.reference.collection('students').stream())),
                'year': dept_data.get('year', [])
            })

        # Render departments in card view
        return render(request, 'list_departments.html', {'departments': departments})
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)

# View to display students and allow posting news for a department
def department_details(request, dept_id):
    try:
        # Fetch department data
        dept_ref = admin_db.collection('departments').document(dept_id)
        dept_data = dept_ref.get().to_dict()

        if not dept_data:
            return JsonResponse({'success': False, 'message': 'Department not found'}, status=404)

        # Fetch students for this department
        students_ref = dept_ref.collection('students')
        students = [student.to_dict() for student in students_ref.stream()]

        return render(request, 'news_department_details.html', {
            'department': dept_data,
            'dept_id': dept_id,
            'students': students,
        })
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


import io
import datetime
from googleapiclient.http import MediaIoBaseUpload
from django.http import JsonResponse
from django.shortcuts import render
from google.oauth2 import service_account
from googleapiclient.discovery import build
from google.cloud import firestore
from django.conf import settings

# Set your Google Drive folder ID here
DRIVE_NEWS_FOLDER_ID = "1CaayOb_77nW7BDJ66jvsYWBokAmwMOmP"

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
import datetime
import io
from googleapiclient.http import MediaIoBaseUpload

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
import datetime
import io
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.discovery import build

from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.discovery import build
import datetime
import io

@login_required
def upload_news(request):
    try:
        print("Starting the upload_news function.")
        parent_folder_id = DRIVE_NEWS_FOLDER_ID
        print(f"Parent folder ID for Google Drive: {parent_folder_id}")

        # Initialize Google Drive service
        try:
            drive_service = build('drive', 'v3', credentials=credentials)
            print("Google Drive API initialized successfully.")
        except Exception as e:
            print(f"Error initializing Google Drive API: {e}")
            return JsonResponse({"success": False, "message": "Failed to initialize Google Drive API."}, status=500)

        # Handle POST requests for news uploads
        if request.method == 'POST':
            print("Processing POST request for news upload.")

            # Extract form data
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()
            print(f"Title: {title}, Description: {description}")

            if not title:
                print("Error: Title is required but not provided.")
                return JsonResponse({"success": False, "message": "Title is required"}, status=400)

            file_url = None  # Default value if no file is uploaded

            # Process file attachment if provided
            if 'attachment' in request.FILES:
                print("File attachment detected, starting upload process.")
                file = request.FILES['attachment']
                file_name = file.name
                print(f"File Name: {file_name}")

                file_metadata = {
                    "name": file_name,
                    "parents": [parent_folder_id]
                }
                file_content = io.BytesIO(file.read())
                media = MediaIoBaseUpload(file_content, mimetype=file.content_type, resumable=True)

                try:
                    print(f"Uploading file '{file_name}' to Google Drive...")
                    uploaded_file = drive_service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields="id, webViewLink, webContentLink"
                    ).execute()
                    print(f"File uploaded successfully: {uploaded_file}")
                    file_url = uploaded_file.get("webViewLink")
                except Exception as e:
                    print(f"Error uploading file to Google Drive: {e}")
                    return JsonResponse({"success": False, "message": "Failed to upload file to Google Drive."}, status=500)

            # Fetch staff details
            staff_email = request.session.get('staff_id', 'Unknown User')
            print(f"Staff Email: {staff_email}")

            staff_profile_ref = staff_db.collection('staff_profiles').document(staff_email)
            staff_profile = staff_profile_ref.get().to_dict() if staff_profile_ref.get().exists else {}
            staff_name = staff_profile.get('name', 'Unknown Name')
            print(f"Staff Name: {staff_name}")

            # Prepare metadata for Firestore
            news_data = {
                'title': title,
                'description': description,
                'file_url': file_url,
                'uploaded_by': staff_email,
                'uploaded_by_name': staff_name,
                'uploaded_at': datetime.datetime.utcnow(),
            }
            print(f"News data prepared: {news_data}")

            # Store metadata in Firestore
            try:
                print("Adding news metadata to Firestore (admin_db)...")
                admin_db.collection('news').add(news_data)
                print("News metadata added to admin_db successfully.")

                print("Adding news metadata to Firestore (staff_db)...")
                staff_db.collection('news').add(news_data)
                print("News metadata added to staff_db successfully.")
            except Exception as e:
                print(f"Error adding news to Firestore: {e}")
                return JsonResponse({"success": False, "message": "Failed to add news metadata to Firestore."}, status=500)

            # Successful response
            print("News uploaded successfully, sending response.")
            return JsonResponse({
                "success": True,
                "message": "News uploaded successfully!",
                "file_url": file_url,
            })

        elif request.method == 'GET':
            print("Rendering the upload news form (GET request).")
            return render(request, 'post_common_news.html')

    except Exception as e:
        print(f"An error occurred in upload_news: {e}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)


    except Exception as e:
        print(f"Error: {str(e)}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)



@login_required
def post_common_news(request):
    """View to handle posting and fetching news."""
    try:
        if request.method == "POST":
            # Handle news posting
            title = request.POST.get("title", "").strip()
            description = request.POST.get("description", "").strip()

            if not title or not description:
                return render(request, 'post_common_news.html', {
                    "news_list": fetch_all_news(),
                    "error": "Title and description are required."
                })

            file_url = None

            # Handle attachment upload
            if 'attachment' in request.FILES:
                file = request.FILES['attachment']
                file_name = file.name

                file_metadata = {
                    "name": file_name,
                    "parents": [DRIVE_NEWS_FOLDER_ID],
                }
                file_content = io.BytesIO(file.read())
                media = MediaIoBaseUpload(file_content, mimetype=file.content_type, resumable=True)

                try:
                    drive_service = build('drive', 'v3', credentials=credentials)
                    uploaded_file = drive_service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields="id, webViewLink"
                    ).execute()
                    file_url = uploaded_file.get("webViewLink")
                except Exception as e:
                    print(f"Error uploading file to Google Drive: {e}")
                    return render(request, 'post_common_news.html', {
                        "news_list": fetch_all_news(),
                        "error": "Failed to upload file. Please try again."
                    })

            # Add news to Firestore
            staff_email = request.session.get('staff_id', 'Unknown User')
            news_data = {
                "title": title,
                "description": description,
                "file_url": file_url,
                "uploaded_by": staff_email,
                "uploaded_at": datetime.datetime.utcnow(),
            }

            staff_db.collection("news").add(news_data)
            admin_db.collection("news").add(news_data)

            return redirect("post_common_news")

        # For GET request, fetch and display all news
        return render(request, "post_common_news.html", {"news_list": fetch_all_news()})

    except Exception as e:
        print(f"Error in post_common_news view: {e}")
        return JsonResponse({"success": False, "message": "An error occurred."}, status=500)


from django.utils.timezone import localtime
import pytz
from django.core.cache import cache
import pytz
import datetime

def fetch_all_news(page=1, limit=10):
    """Fetch paginated news from Firestore with caching and optimized queries."""
    cache_key = f'news_list_page_{page}'  # Cache key for the specific page
    cached_news = cache.get(cache_key)
    
    if cached_news:
        # Return cached data if available
        return cached_news

    try:
        # Define the timezone to format the timestamps
        user_timezone = pytz.timezone('Asia/Kolkata')  # Adjust as needed

        news_collection = staff_db.collection("news")
        
        # Firestore query with pagination (limit & offset for pagination)
        news_docs = (
            news_collection
            .order_by("uploaded_at", direction="DESCENDING")
            .offset((page - 1) * limit)  # Skip documents based on the page number
            .limit(limit)  # Limit the number of documents fetched
            .stream()
        )

        news_list = []

        for doc in news_docs:
            news_data = doc.to_dict()
            if "uploaded_at" in news_data:
                try:
                    uploaded_at = news_data["uploaded_at"]

                    # Convert to local timezone
                    localized_time = uploaded_at.astimezone(user_timezone)

                    # Format the timestamp in a readable way
                    news_data["uploaded_at"] = localized_time.strftime('%B %d, %Y at %I:%M:%S ')
                except Exception as e:
                    print(f"Error formatting timestamp for news ID {doc.id}: {e}")

            # Add the news item to the list
            news_list.append({
                "id": doc.id,
                **news_data,
            })

        # Cache the result for subsequent access (timeout set to 10 minutes)
        cache.set(cache_key, news_list, timeout=600)  # Cache for 10 minutes

        return news_list
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []


import datetime
import io
from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.discovery import build



from django.contrib import messages
from django.shortcuts import redirect

@login_required
def delete_news(request, news_id):
    """Delete individual news and its associated file."""
    try:
        # Fetch the news document
        news_ref = staff_db.collection('news').document(news_id)
        news_data = news_ref.get().to_dict()

        if news_data and 'file_url' in news_data:
            # Extract Google Drive file ID from the file URL
            file_id = news_data['file_url'].split('/')[-2]
            try:
                drive_service = build('drive', 'v3', credentials=credentials)
                drive_service.files().delete(fileId=file_id).execute()
                print(f"Deleted file with ID: {file_id}")
            except Exception as e:
                print(f"Error deleting file from Google Drive: {e}")

        # Delete the news from Firestore (both staff and admin DBs)
        staff_db.collection('news').document(news_id).delete()
        admin_db.collection('news').document(news_id).delete()
        print(f"Deleted news with ID: {news_id}")

        # Add success message
        messages.success(request, "News deleted successfully!")
        return redirect('post_common_news')  
    except Exception as e:
        print(f"Error deleting news: {e}")
        messages.error(request, "Failed to delete news.")
        return redirect('post_common_news')  


@login_required
def delete_all_news(request):
    """Delete all news and their associated files."""
    try:
        news_docs = staff_db.collection('news').stream()
        drive_service = build('drive', 'v3', credentials=credentials)

        for doc in news_docs:
            news_data = doc.to_dict()
            news_id = doc.id

            # Check if 'file_url' exists and is not None
            file_url = news_data.get('file_url')
            if file_url:
                try:
                    file_id = file_url.split('/')[-2]
                    drive_service.files().delete(fileId=file_id).execute()
                    print(f"Deleted file with ID: {file_id}")
                except Exception as e:
                    print(f"Error deleting file from Google Drive: {e}")

            # Delete news from Firestore (both staff and admin DBs)
            try:
                staff_db.collection('news').document(news_id).delete()
                admin_db.collection('news').document(news_id).delete()
                print(f"Deleted news with ID: {news_id}")
            except Exception as e:
                print(f"Error deleting news with ID {news_id}: {e}")

        messages.success(request, "News deleted successfully!")
        return redirect('post_common_news') 
    except Exception as e:
        print(f"Error deleting all news: {e}")
        messages.error(request, "Failed to delete news.")
        return redirect('post_common_news')  

import datetime
import io
from googleapiclient.http import MediaIoBaseUpload
from googleapiclient.discovery import build
from django.shortcuts import render
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required



@login_required
def edit_news(request, news_id):
    """Edit news details."""
    try:
        news_ref = staff_db.collection('news').document(news_id)
        news_doc = news_ref.get()

        # Check if document exists
        if not news_doc.exists:
            return JsonResponse({"success": False, "message": "News item not found."}, status=404)

        news_data = news_doc.to_dict()  # Convert the DocumentSnapshot to a dictionary

        if request.method == 'POST':
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()

            if not title or not description:
                return JsonResponse({"success": False, "message": "Title and Description are required."}, status=400)

            # Update fields in Firestore
            updated_data = {
                'title': title,
                'description': description,
                'updated_at': datetime.datetime.utcnow(),
            }

            # Handle new file attachment
            if 'attachment' in request.FILES:
                file = request.FILES['attachment']
                file_name = file.name
                file_metadata = {
                    "name": file_name,
                    "parents": [DRIVE_NEWS_FOLDER_ID]
                }
                file_content = io.BytesIO(file.read())
                media = MediaIoBaseUpload(file_content, mimetype=file.content_type, resumable=True)

                try:
                    drive_service = build('drive', 'v3', credentials=credentials)

                    # Delete old file if it exists
                    old_file_id = None
                    if 'file_url' in news_data:  # Check in the converted dictionary
                        old_file_id = news_data['file_url'].split('/')[-2]
                    if old_file_id:
                        drive_service.files().delete(fileId=old_file_id).execute()

                    # Upload new file
                    uploaded_file = drive_service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields="id, webViewLink"
                    ).execute()
                    updated_data['file_url'] = uploaded_file.get("webViewLink")
                except Exception as e:
                    print(f"Error uploading new file: {e}")
                    return JsonResponse({"success": False, "message": "Failed to upload new file."}, status=500)

            # Update Firestore document
            news_ref.update(updated_data)
            return JsonResponse({"success": True, "message": "News updated successfully!"})

        else:
              # If GET request, show the current news data in the form
            return render(request, 'edit_news.html', {'news_data': news_data})

    except Exception as e:
        print(f"Error editing news: {e}")
        return JsonResponse({"success": False, "message": "An error occurred while editing news."}, status=500)



import datetime
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from django.http import JsonResponse
from django.shortcuts import render
from django.contrib.auth.decorators import login_required




@login_required
def upload_news_by_department(request, dept_id):
    DRIVE_NEWS_FOLDER_ID = "1CaayOb_77nW7BDJ66jvsYWBokAmwMOmP"  # Parent folder ID in Google Drive

    """Handle posting news for a specific department."""
    try:
        # Fetch department details from Firestore
        department_ref = admin_db.collection('departments').document(dept_id)
        department = department_ref.get().to_dict()

        if not department:
            return JsonResponse({"success": False, "message": "Department not found."}, status=404)

        # Dynamically create folder name (e.g., I-MCA, II-MCA)
        dept_folder_name = f"{department['year']}-{department['name']}"

        # Initialize Google Drive API
        try:
            drive_service = build('drive', 'v3', credentials=credentials)
        except Exception as e:
            return JsonResponse({"success": False, "message": "Google Drive API initialization failed."}, status=500)

        # Check for existing folder within the parent folder
        query = (
            f"mimeType = 'application/vnd.google-apps.folder' and "
            f"name = '{dept_folder_name}' and '{DRIVE_NEWS_FOLDER_ID}' in parents"
        )
        results = drive_service.files().list(q=query).execute()
        folders = results.get('files', [])

        if not folders:
            # Folder does not exist; create it under the parent folder
            folder_metadata = {
                'name': dept_folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [DRIVE_NEWS_FOLDER_ID]
            }
            folder = drive_service.files().create(body=folder_metadata, fields='id').execute()
            folder_id = folder['id']
        else:
            # Folder already exists
            folder_id = folders[0]['id']

        if request.method == 'POST':
            # Fetch news details from POST request
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()

            if not title or not description:
                return JsonResponse({"success": False, "message": "Title and description are required."}, status=400)

            file_url = None  # Initialize file URL variable

            # Handle file attachment upload
            if 'attachment' in request.FILES:
                file = request.FILES['attachment']
                file_metadata = {
                    "name": file.name,
                    "parents": [folder_id]  # Store file in the department's folder
                }
                media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.content_type, resumable=True)

                try:
                    uploaded_file = drive_service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields="id, webViewLink"
                    ).execute()
                    file_url = uploaded_file.get("webViewLink")  # Get the public view link
                except Exception as e:
                    return JsonResponse({"success": False, "message": "Failed to upload file to Google Drive."}, status=500)

            # Get staff details
            staff_email = request.session.get('staff_id', 'Unknown User')
            staff_profile_ref = staff_db.collection('staff_profiles').document(staff_email)
            staff_profile = staff_profile_ref.get().to_dict() if staff_profile_ref.get().exists else {}
            staff_name = staff_profile.get('name', 'Unknown Name')

            # Prepare news data
            news_data = {
                'title': title,
                'description': description,
                'file_url': file_url,
                'uploaded_by': staff_email,
                'uploaded_by_name': staff_name,
                'uploaded_at': datetime.datetime.utcnow()  # Use UTC time for consistency
            }

            # Save news data in the department's "news" subcollection
            try:
                department_ref.collection('news').add(news_data)
            except Exception as e:
                return JsonResponse({"success": False, "message": "Failed to save news in Firestore."}, status=500)

            return JsonResponse({"success": True, "message": "News posted successfully."})

        # For GET request, render the form
        return render(request, 'post_common_news.html', {'department': department})

    except Exception as e:
        print(f"Error in upload_news_by_department view: {e}")
        return JsonResponse({"success": False, "message": str(e)}, status=500)

from django.contrib.auth.decorators import login_required
import pytz

@login_required
def post_news_page(request, dept_id):
    """View to fetch and render news for a specific department."""
    try:
        # Fetch the department details
        department_ref = admin_db.collection('departments').document(dept_id)
        department = department_ref.get().to_dict()

        if not department:
            return JsonResponse({"success": False, "message": "Department not found."}, status=404)

        
        # Add dept_id to the department dictionary
        department['id'] = dept_id

        # Fetch news for the department
        news_list = fetch_news(dept_id)

        # Render the news page with the department and news data
        return render(request, "post_news_page.html", {
            "news_list": news_list,
            "department": department,
        })
    except Exception as e:
        print(f"Error in post_news_page view: {e}")
        return JsonResponse({"success": False, "message": "An error occurred."}, status=500)

def fetch_news(dept_id):
    """Fetch news for a specific department."""
    try:
        department_ref = admin_db.collection('departments').document(dept_id)
        news_collection = department_ref.collection('news')
        news_docs = news_collection.order_by('uploaded_at', direction='DESCENDING').stream()

        news_list = []
        user_timezone = pytz.timezone('Asia/Kolkata')

        for doc in news_docs:
            news_data = doc.to_dict()
            if "uploaded_at" in news_data:
                uploaded_at = news_data["uploaded_at"]
                localized_time = uploaded_at.astimezone(user_timezone)
                news_data["uploaded_at"] = localized_time.strftime('%B %d, %Y at %I:%M:%S %p')

            news_list.append({"id": doc.id, **news_data})

        return news_list
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []


@login_required
def delete_department_news(request, dept_id, news_id):
    """Delete news and its associated file from Google Drive and Firestore."""
    try:
        # Fetch the news document from the department's news subcollection
        department_ref = admin_db.collection('departments').document(dept_id)
        news_ref = department_ref.collection('news').document(news_id)
        news_data = news_ref.get().to_dict()

        if not news_data:
            messages.error(request, "News not found.")
            return redirect('post_common_news', dept_id=dept_id)

        # Check if the news has an associated file URL
        if 'file_url' in news_data and news_data['file_url']:
            try:
                # Extract the Google Drive file ID from the file URL
                file_id = news_data['file_url'].split('/')[-2]

                # Initialize Google Drive API and delete the file
                drive_service = build('drive', 'v3', credentials=credentials)
                drive_service.files().delete(fileId=file_id).execute()
                print(f"Deleted file from Google Drive with ID: {file_id}")
            except Exception as e:
                print(f"Error deleting file from Google Drive: {e}")
                messages.warning(request, "Failed to delete the associated file from Google Drive.")

        # Delete the news document from Firestore (admin DB)
        news_ref.delete()
        print(f"Deleted news from department {dept_id}, ID: {news_id}")

        # Optionally delete the news document from the staff database, if required
        staff_news_ref = staff_db.collection('news').document(news_id)
        if staff_news_ref.get().exists:
            staff_news_ref.delete()
            print(f"Deleted news from staff DB, ID: {news_id}")

        messages.success(request, "News deleted successfully!")
        return redirect('post_news_page', dept_id=dept_id)

    except Exception as e:
        print(f"Error deleting news: {e}")
        messages.error(request, "Failed to delete news.")
        return redirect('post_news_page', dept_id=dept_id)

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

@login_required
def delete_all_department_news(request, dept_id):
    """Delete all news and associated folder for a specific department."""
    try:
        # Fetch department reference
        department_ref = admin_db.collection('departments').document(dept_id)
        department = department_ref.get().to_dict()

        if not department:
            messages.error(request, "Department not found.")
            return redirect('post_common_news', dept_id=dept_id)

        # Construct the Google Drive folder name (e.g., "I-MCA", "II-MCA")
        dept_folder_name = f"{department['year']}-{department['name']}"

        # Initialize Google Drive API
        try:
            drive_service = build('drive', 'v3', credentials=credentials)
        except HttpError as e:
            print(f"Google Drive API initialization error: {e}")
            messages.error(request, "Failed to connect to Google Drive.")
            return redirect('post_news_page', dept_id=dept_id)

        # Find the folder on Google Drive
        query = f"mimeType = 'application/vnd.google-apps.folder' and name = '{dept_folder_name}'"
        folder_results = drive_service.files().list(q=query).execute()
        folders = folder_results.get('files', [])

        if folders:
            folder_id = folders[0]['id']
            try:
                # Delete the folder and its contents
                drive_service.files().delete(fileId=folder_id).execute()
                print(f"Deleted folder with ID: {folder_id}")
            except HttpError as e:
                print(f"Error deleting Google Drive folder: {e}")
                messages.warning(request, "Failed to delete folder on Google Drive.")

        # Delete all news documents from Firestore
        try:
            news_collection_ref = department_ref.collection('news')
            news_docs = news_collection_ref.stream()
            for doc in news_docs:
                doc.reference.delete()
            print(f"All news deleted for department: {dept_id}")
        except Exception as e:
            print(f"Error deleting Firestore news documents: {e}")
            messages.warning(request, "Failed to delete news documents in Firestore.")

        # Add success message
        messages.success(request, "All news deleted successfully.")
    except Exception as e:
        print(f"Error in delete_all_department_news: {e}")
        messages.error(request, "Failed to delete all news.")

    # Redirect back to the department news page
    return redirect('post_news_page', dept_id=dept_id)


from googleapiclient.http import MediaIoBaseUpload

@login_required
def edit_department_news(request, dept_id, news_id):
    """Edit news details in a specific department."""
    try:
        # Fetch the department and its news document
        department_ref = admin_db.collection('departments').document(dept_id)
        news_ref = department_ref.collection('news').document(news_id)
        news_doc = news_ref.get()

        if not news_doc.exists:
            return JsonResponse({"success": False, "message": "News item not found."}, status=404)

        news_data = news_doc.to_dict()  # Convert the DocumentSnapshot to a dictionary

        if request.method == 'POST':
            # Fetch new title and description from the form
            title = request.POST.get('title', '').strip()
            description = request.POST.get('description', '').strip()

            if not title or not description:
                return JsonResponse({"success": False, "message": "Title and Description are required."}, status=400)

            # Prepare updated data
            updated_data = {
                'title': title,
                'description': description,
                'updated_at': datetime.datetime.utcnow(),
            }

            # Handle file attachment
            if 'attachment' in request.FILES:
                file = request.FILES['attachment']
                file_metadata = {
                    "name": file.name,
                    "parents": [DRIVE_NEWS_FOLDER_ID]
                }
                media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.content_type, resumable=True)

                try:
                    # Initialize Google Drive service
                    drive_service = build('drive', 'v3', credentials=credentials)

                    # Delete old file if it exists
                    old_file_id = None
                    if 'file_url' in news_data:
                        old_file_id = news_data['file_url'].split('/')[-2]
                    if old_file_id:
                        drive_service.files().delete(fileId=old_file_id).execute()

                    # Upload the new file
                    uploaded_file = drive_service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields="id, webViewLink"
                    ).execute()
                    updated_data['file_url'] = uploaded_file.get("webViewLink")
                except Exception as e:
                    print(f"Error uploading new file: {e}")
                    return JsonResponse({"success": False, "message": "Failed to upload the new file."}, status=500)

            # Update Firestore document in the department's collection
            news_ref.update(updated_data)
            messages.success(request, "News updated successfully!")
            return redirect('post_common_news', dept_id=dept_id)

        else:
            # If GET request, render the edit form with existing news data
            return render(request, 'edit_news.html', {'news_data': news_data, 'dept_id': dept_id})

    except Exception as e:
        print(f"Error editing department news: {e}")
        messages.error(request, "An error occurred while editing news.")
        return redirect('post_common_news', dept_id=dept_id)


from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
import datetime


import pytz
import datetime

@login_required
def post_videos(request):
    """Handle video tutorial addition and retrieval."""
    try:
        # Reference to Firestore collections
        staff_videos_ref = staff_db.collection('videos')
        admin_videos_ref = admin_db.collection('videos')

        if request.method == 'POST':
            title = request.POST.get('title', '').strip()
            link = request.POST.get('link', '').strip()

            if not title or not link:
                messages.error(request, "Title and link are required!")
                return redirect('post_videos')

            # Get staff email and name from the staff profile (assuming it's available)
            staff_email = request.session.get('staff_id', 'Unknown User')
            staff_profile_ref = staff_db.collection('staff_profiles').document(staff_email)
            staff_profile = staff_profile_ref.get().to_dict() if staff_profile_ref.get().exists else {}
            staff_name = staff_profile.get('name', 'Unknown Name')

            # Prepare video data (including uploaded_by and uploaded_by_name)
            video_data = {
                'title': title,
                'link': link,
                'uploaded_by': staff_email,
                'uploaded_by_name': staff_name,
                'uploaded_at': datetime.datetime.utcnow(),
            }

            # Save video data in both staff and admin databases
            staff_videos_ref.add(video_data)
            admin_videos_ref.add(video_data)
            messages.success(request, "Video tutorial added successfully!")
            return redirect('post_videos')

        # Retrieve videos for display, limit to batch fetching
        staff_videos = staff_videos_ref.stream()
        grouped_videos = {}

        # Group videos by upload date and convert uploaded_at to local time
        local_timezone = pytz.timezone('Asia/Kolkata')
        for video in staff_videos:
            video_data = video.to_dict()

            # Ensure video_id is available and correct
            video_id = video.id  # This should be available for Firestore documents
            if not video_id:
                print(f"Error: video ID is missing for video: {video_data}")  # Debugging

            # Convert the uploaded_at time to a local timezone only once
            uploaded_at_utc = video_data['uploaded_at']
            uploaded_at_local = uploaded_at_utc.astimezone(local_timezone)
            video_data['uploaded_at_local'] = uploaded_at_local.strftime('%B %d, %Y at %I:%M:%S %p')

            # Get the video ID to include in the URL
            video_data['video_id'] = video_id  # Assign video_id to the video data

            # Group videos by upload date
            upload_date = uploaded_at_local.strftime('%Y-%m-%d')
            if upload_date not in grouped_videos:
                grouped_videos[upload_date] = []
            grouped_videos[upload_date].append(video_data)

        return render(request, 'post_videos.html', {'grouped_videos': grouped_videos})

    except Exception as e:
        print(f"Error in post_videos view: {e}")
        messages.error(request, "An error occurred while processing the request.")
        return redirect('post_videos')



@login_required
def edit_video(request, video_id):
    """Handle video tutorial edit."""
    try:
        # Reference to Firestore video document
        video_ref = staff_db.collection('videos').document(video_id)
        video_doc = video_ref.get()

        if not video_doc.exists:
            messages.error(request, "Video not found!")
            return redirect('post_videos')

        video_data = video_doc.to_dict()

        if request.method == 'POST':
            # Get updated data from the form
            title = request.POST.get('title', '').strip()
            link = request.POST.get('link', '').strip()

            if not title or not link:
                messages.error(request, "Both title and link are required!")
                return redirect('edit_video', video_id=video_id)

            # Update video details
            video_ref.update({
                'title': title,
                'link': link,
                'updated_at': datetime.datetime.utcnow()
            })

            # Update the video in the admin database as well
            admin_video_query = admin_db.collection('videos').where('uploaded_by', '==', video_data['uploaded_by']).where('title', '==', video_data['title']).stream()
            for doc in admin_video_query:
                admin_video_ref = admin_db.collection('videos').document(doc.id)
                admin_video_ref.update({
                    'title': title,
                    'link': link,
                    'updated_at': datetime.datetime.utcnow()
                })

            messages.success(request, "Video tutorial updated successfully!")
            return redirect('post_videos')

        # Format uploaded_at for display
        local_timezone = pytz.timezone('Asia/Kolkata')
        if 'uploaded_at' in video_data:
            uploaded_at_utc = video_data['uploaded_at']
            uploaded_at_local = uploaded_at_utc.astimezone(local_timezone)
            video_data['uploaded_at_local'] = uploaded_at_local.strftime('%B %d, %Y at %I:%M:%S %p')

        return render(request, 'edit_video.html', {'video': video_data, 'video_id': video_id})

    except Exception as e:
        print(f"Error in edit_video view: {e}")
        messages.error(request, f"An unexpected error occurred: {e}")
        return redirect('post_videos')


@login_required
def delete_video(request, video_id):
    """Handle video tutorial deletion."""
    try:
        video_ref = staff_db.collection('videos').document(video_id)
        video_ref.delete()
        messages.success(request, "Video tutorial deleted successfully!")
    except Exception as e:
        messages.error(request, f"Failed to delete video tutorial: {e}")

    return redirect('post_videos')

from django.shortcuts import render
import datetime

def leaderboard_view(request):
    try:
        # Get all departments from Firestore
        departments_ref = admin_db.collection('departments')
        departments = list(departments_ref.stream())  # Convert to a list for re-use in logs
        
        print(f"Departments: {[dept.id for dept in departments]}")  # Debug log
        
        students = []
        total_solves = 0
        total_posts = 0
        weekly_participants = []
        current_week_start = datetime.datetime.now() - datetime.timedelta(days=7)

        for dept in departments:
            try:
                print(f"Processing department: {dept.id}")  # Debug log
                
                # Fetch the students subcollection
                students_ref = dept.reference.collection('students')
                student_docs = list(students_ref.stream())
                
                print(f"Found {len(student_docs)} students in department {dept.id}")  # Debug log
                
                for student in student_docs:
                    student_data = student.to_dict()
                    if not student_data:  # Handle empty student documents
                        print(f"Empty student data for {student.id}")
                        continue
                    
                    # Extract and validate fields
                    name = student_data.get('name', 'Unknown')
                    solves = student_data.get('solves', 0)
                    posts = student_data.get('posts', 0)
                    profile_image = student_data.get('profile_image', '/static/images/default_profile.jpg')
                    last_participation = student_data.get('last_participation')
                    
                    if last_participation:
                        last_participation = last_participation.to_pydatetime()
                    else:
                        last_participation = datetime.datetime.min

                    # Add to students list
                    students.append({
                        'id': student.id,
                        'name': name,
                        'solves': solves,
                        'posts': posts,
                        'profile_image': profile_image,
                        'last_participation': last_participation,
                    })

                    total_solves += solves
                    total_posts += posts

                    # Weekly participants
                    if last_participation > current_week_start:
                        weekly_participants.append({'name': name, 'solves': solves})
            
            except Exception as dept_error:
                print(f"Error processing department {dept.id}: {dept_error}")
                continue  # Skip department on error

        # Sort students by solves
        students = sorted(students, key=lambda x: x['solves'], reverse=True)

        # Determine winner
        winner = students[0] if students else None

        # Calculate solving ratio and online ratio
        solving_ratio = total_solves / total_posts if total_posts > 0 else 0
        online_students = [s for s in students if s.get('is_online', False)]
        online_ratio = len(online_students) / len(students) if students else 0

        # Render the leaderboard
        return render(request, 'leaderboard.html', {
            'students': students,
            'weekly_participants': weekly_participants,
            'winner': winner,
            'total_solves': total_solves,
            'total_posts': total_posts,
            'solving_ratio': solving_ratio,
            'online_ratio': online_ratio,
        })

    except Exception as e:
        print(f"Error: {e}")
        return render(request, 'leaderboard.html', {'message': f"An error occurred: {e}"})
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from firebase_admin import firestore
import datetime

@login_required(login_url='/staff/login/')
def post_questions(request):
    """Display post questions page along with all posted questions."""
    try:
        # Fetch all questions from Firestore
        questions = admin_db.collection('coding_questions').stream()

        # Convert documents into a list of dictionaries, adding the document ID
        all_questions = [
            {**doc.to_dict(), 'id': doc.id} for doc in questions
        ]

        # Render the page with the questions
        return render(request, 'post_questions.html', {'questions': all_questions})

    except Exception as e:
        # Log any exceptions
        print(f"Error fetching questions: {e}")
        messages.error(request, "Unable to fetch questions.")
        return redirect('post_questions')

@login_required(login_url='/staff/login/')
def question_background(request):
    """Step 1: Gather background information for the question."""
    if request.method == 'POST':
        background = request.POST.get('background', '').strip()
        difficulty = request.POST.get('difficulty', '').strip()
        company_tags = request.POST.get('company_tags', '').strip()
        topic_tags = request.POST.get('topic_tags', '').strip()

        # Validate required fields
        if not background or not difficulty:
            messages.error(request, "Background information and difficulty level are required.")
            return redirect('question_background')

        # Save the data to the session
        request.session['background'] = background
        request.session['difficulty'] = difficulty
        
        # Save optional tags if provided
        if company_tags:
            request.session['company_tags'] = [tag.strip() for tag in company_tags.split(',')]
        else:
            request.session['company_tags'] = []  # Set empty list if no company tags entered

        if topic_tags:
            request.session['topic_tags'] = [tag.strip() for tag in topic_tags.split(',')]
        else:
            request.session['topic_tags'] = []  # Set empty list if no topic tags entered

        return redirect('question_details')  # Go to next step
    
    return render(request, 'question_background.html')


@login_required(login_url='/staff/login/')
def question_details(request):
    """Step 2: Gather details about the question."""
    if request.method == 'POST':
        category = request.POST.get('category', '').strip()
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        if not (category and title and description):
            messages.error(request, "All fields are required.")
            return redirect('question_details')
        request.session.update({
            'category': category,
            'title': title,
            'description': description,
        })
        return redirect('question_solution')
    return render(request, 'question_details.html')

@login_required(login_url='/staff/login/')
def question_solution(request):
    """Step 3: Gather the solution or pseudocode."""
    if request.method == 'POST':
        solution = request.POST.get('solution', '').strip()
        if not solution:
            messages.error(request, "Solution or pseudocode is required.")
            return redirect('question_solution')
        request.session['solution'] = solution
        return redirect('question_testcases')
    return render(request, 'question_solution.html')

@login_required(login_url='/staff/login/')
def question_testcases(request):
    """Step 4: Gather test cases for the question."""
    if request.method == 'POST':
        testcases = request.POST.get('testcases', '').strip()
        if not testcases:
            messages.error(request, "Test cases are required.")
            return redirect('question_testcases')
        request.session['testcases'] = testcases
        return redirect('submit_question')
    return render(request, 'question_testcases.html')

@login_required(login_url='/staff/login/')
def submit_question(request):
    """Step 5: Save the question data to Firestore."""
    try:
        if request.method == 'POST':
            # Fetch staff email from session
            staff_email = request.session.get('staff_id')
            if not staff_email:
                messages.error(request, "Session expired or staff not identified. Please log in again.")
                return redirect('/staff/login/')

            # Retrieve staff name from Firestore
            staff_profile_ref = staff_db.collection('staff_profiles').document(staff_email)
            staff_profile = staff_profile_ref.get().to_dict() if staff_profile_ref.get().exists else {}
            staff_name = staff_profile.get('name', 'Unknown Name')

            # Fetch all collected data from session
            question_data = {
                'background': request.session.get('background', ''),
                'category': request.session.get('category', ''),
                'title': request.session.get('title', ''),
                'description': request.session.get('description', ''),
                'solution': request.session.get('solution', ''),
                'testcases': request.session.get('testcases', ''),
                'difficulty': request.session.get('difficulty', ''),  # Include difficulty level
                'company_tags': request.session.get('company_tags', []),  # Save company tags
                'topic_tags': request.session.get('topic_tags', []),  # Save topic tags
                'uploaded_by': {
                    'name': staff_name,
                    'email': staff_email,
                },
                'uploaded_at': datetime.datetime.utcnow(),
            }

            # Debugging - print the data being saved to Firestore
            print("Question Data to be saved: ", question_data)

            # Save question data in both admin and staff databases
            admin_db.collection('coding_questions').add(question_data)
            staff_db.collection('coding_questions').add(question_data)

            # Clear only question-related session data
            for key in ['background', 'category', 'title', 'description', 'solution', 'testcases', 'difficulty', 'company_tags', 'topic_tags']:
                if key in request.session:
                    del request.session[key]

            messages.success(request, "Your question has been submitted successfully!")
            return redirect('posted_questions')

    except Exception as e:
        print(f"Error submitting question: {e}")
        messages.error(request, "Failed to submit the question. Please try again.")
        return redirect('question_testcases')

    return render(request, 'submit_question.html')

@login_required(login_url='/staff/login/')
def posted_questions(request):
    """Fetch and display all posted coding questions."""
    try:
        # Fetch all questions from Firestore
        questions = admin_db.collection('coding_questions').stream()

        # Convert Firestore documents into a list of dictionaries with document IDs
        all_questions = [
            {**doc.to_dict(), 'id': doc.id} for doc in questions
        ]

        # Log the questions for debugging purposes
        print("Fetched Questions:", all_questions)

        # Render the questions to the template
        return render(request, 'posted_questions.html', {'questions': all_questions})

    except Exception as e:
        # Handle and log exceptions
        print(f"Error fetching questions: {e}")
        messages.error(request, "Unable to fetch questions.")
        return redirect('post_questions')

from django.http import JsonResponse
from django.shortcuts import get_object_or_404

@login_required(login_url='/staff/login/')
def delete_question(request, question_id):
    """Delete a posted question from the database."""
    try:
        # Delete the question from Firestore (admin_db and staff_db if applicable)
        admin_db.collection('coding_questions').document(question_id).delete()
        staff_db.collection('coding_questions').document(question_id).delete()

        messages.success(request, "Question deleted successfully.")
        return redirect('posted_questions')

    except Exception as e:
        print(f"Error deleting question: {e}")
        messages.error(request, "Unable to delete the question. Please try again.")
        return redirect('posted_questions')


def discussions(request):
    # Static data for now, later you can query from the database
    return render(request, 'discussions.html')


# View for the Certifications page
def certifications_view(request):
    return render(request, 'certifications.html')



#Logout

from django.shortcuts import redirect
from django.contrib.sessions.models import Session

def logout_view(request):
    try:
        # Manually remove session attributes
        if 'staff_id' in request.session:
            del request.session['staff_id']  # Remove staff email from session
        if 'is_authenticated' in request.session:
            del request.session['is_authenticated']  # Remove authentication status
        
      

        # Redirect user to the login page after logout
        return redirect('/staff/login/')

    except Exception as e:
        print(f"Error logging out: {e}")
        return redirect('/staff/login/')  # Redirect in case of error


from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2.service_account import Credentials
import io
import uuid
import datetime
from django.shortcuts import render, redirect
from django.conf import settings
from django.http import JsonResponse




from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
import uuid
import datetime
from django.conf import settings

def post_css_problem(request):
    DRIVE_CSS_PROBLEMS_FOLDER_ID = "1Ydb3HwVYCZ-zpVEuoVbDfo3lcNHMSAiI"
    try:
        if request.method == "POST":
            
            file_url = None

            if 'image' in request.FILES:
                file = request.FILES['image']
                file_name = file.name

                file_metadata = {
                    "name": file_name,
                    "parents": [DRIVE_CSS_PROBLEMS_FOLDER_ID],
                }
                file_content = io.BytesIO(file.read())
                media = MediaIoBaseUpload(file_content, mimetype=file.content_type, resumable=True)

                try:
                    
                    drive_service = build('drive', 'v3', credentials=credentials)

                    uploaded_file = drive_service.files().create(
                        body=file_metadata,
                        media_body=media,
                        fields="id, webViewLink"
                    ).execute()
                    file_url = uploaded_file.get("webViewLink")

                except Exception as e:
                    print(f"Error uploading file to Google Drive: {e}")
                    return render(request, 'post_css_problem.html', {
                        "css_problems": fetch_all_css_problems(),
                        "error": "Failed to upload file. Please try again."
                    })

            problem_id = str(uuid.uuid4())

            problem_data = {
                "id": problem_id,
                "image_url": file_url,
                "uploaded_by": request.user.email,
                "uploaded_at": datetime.datetime.utcnow(),
            }

            staff_db.collection("css_problems").document(problem_id).set(problem_data)

            return redirect("post_css_problem")

        return render(request, "post_css_problem.html", {"css_problems": fetch_all_css_problems()})

    except Exception as e:
        print(f"Error in post_css_problem view: {e}")
        return JsonResponse({"success": False, "message": "An error occurred."}, status=500)


def fetch_all_css_problems():
    """Fetch all CSS problems from Firestore."""
    problems_ref = staff_db.collection("css_problems").order_by("uploaded_at", direction=firestore.Query.DESCENDING).stream()
    return [problem.to_dict() for problem in problems_ref]

