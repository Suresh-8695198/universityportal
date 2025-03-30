from django.urls import path
from . import views



urlpatterns = [
    path('', views.landing_page, name='landing_page'),
    path('admin/login/', views.admin_login, name='admin_login'),
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('forgot-password/', views.admin_forgot_password, name='admin_forgot_password'),
    path('verify-otp/', views.verify_otp, name='verify_otp'),
    path('reset-password/', views.reset_password, name='reset_password'),




    path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/departments/', views.manage_departments, name='manage_departments'),
    path('admin/departments/edit/<str:dept_id>/', views.edit_department, name='edit_department'),
    path('admin/departments/delete/<str:dept_id>/', views.delete_department, name='delete_department'),
    path('admin/students/', views.manage_students, name='manage_students'),
    path('admin/staff/', views.manage_staff, name='manage_staff'),
    path('admin/staff/edit/<int:staff_id>/', views.edit_staff, name='edit_staff'),
    path('admin/staff/delete/<int:staff_id>/', views.delete_staff, name='delete_staff'),
    path('admin/news/', views.post_news, name='post_news'),
    path('department/<int:dept_id>/students/', views.department_students, name='department_students'),
    

    path('add-student/', views.add_student, name='add_student'),
    path('get_students_by_department/', views.get_students_by_department, name='get_students_by_department'),
    path('manage-students/', views.manage_students, name='manage_students'),
    # Edit student - dynamic department_id and student_id
    path('edit_student/<str:department_id>/<str:student_id>/', views.edit_student, name='edit_student'),
    path('upload-excel/', views.upload_excel, name='upload_excel'),
    # Delete student - dynamic department_id and student_id
    path('delete_student/<str:department_id>/<str:student_id>/', views.delete_student, name='delete_student'),
    path('delete_all_students/<str:department_id>/', views.delete_all_students, name='delete_all_students'),
    path('get_students/<str:dept_id>/', views.get_students, name='get_students'),

    path('manage-staff/', views.manage_staff, name='manage_staff'),
    path('get-staff/', views.get_staff, name='get_staff'),
    path('staff-upload-excel/', views.staff_upload_excel, name='staff_upload_excel'),
    path('edit-staff/<str:staff_id>/', views.edit_staff, name='edit_staff'),
    path('fetch-staff/<str:staff_id>/', views.fetch_staff, name='fetch_staff'),
    path('delete-staff/<str:staff_id>/', views.delete_staff, name='delete_staff'),



        
        path('statistics/', views.statistics, name='statistics'),
     
         path('admin/login/', views.admin_login, name='admin_login'),  # This should be your login view
    path('admin-profile/', views.admin_profile, name='admin_profile'),
    path('change-password/', views.change_password, name='change_password'),
  # path('accounts/login/', views.custom_login, name='login'), 


   path('logout/', views.logout, name='logout'),   # Use
]
