from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.staff_login, name='staff_login'),
    path('dashboard/', views.staff_dashboard, name='staff_dashboard'),
    path('home', views.home, name='home'),

    # Staff profile page
    path('profile/', views.staff_profile, name='staff_profile'),
    
    # Logout route
    #path('logout/', views.logout, name='staff_logout'),
    
    # Delete account route
    #path('delete_account/', views.delete_account, name='staff_delete_account'),




    #Assignments page
    path('assignments/', views.assignments_page, name='assignments'),
    path('department/<str:dept_id>/', views.view_department, name='view_department'),
    path('department/<str:dept_id>/assignments/', views.post_assignment, name='post_assignment'),
    #path('department/<str:dept_id>/quizzes/', views.post_quiz, name='post_quiz'),
    #path('department/<str:dept_id>/<str:context_type>/', views.view_department, name='view_department'),


    #Post Notes page
    path('post_notes/', views.post_notes_page, name='post_notes'),
    path('list_department/<str:dept_id>/', views.list_department, name='list_department'),
    path('upload_notes/<str:dept_id>/<str:class_name>/', views.upload_to_drive, name='upload_to_drive'), 
    path('preview_pdf/<str:file_id>/', views.preview_pdf, name='preview_pdf'),
    path('download/<str:file_id>/', views.download_from_drive, name='download_from_drive'),
    path('delete_from_drive/<str:file_id>/<str:dept_id>/<str:class_name>/', views.delete_from_drive, name='delete_from_drive'),
    #path('files/', views.view_uploaded_files, name='view_uploaded_files'),



    #Post News

    path('show_all_departments/', views.show_departments, name='show_departments'),
    path('news_department/<str:dept_id>/', views.department_details, name='department_details'),
    #path('post_news/<str:dept_id>/', views.post_news, name='post_news_department'),
   
    path('upload-news/', views.upload_news, name='upload_news'), 
    path("post-common-news/", views.post_common_news, name="post_common_news"),
    path("news/delete/<str:news_id>/", views.delete_news, name="delete_news"),
    path("news/delete_all/", views.delete_all_news, name="delete_all_news"),
    path("news/edit/<str:news_id>/", views.edit_news, name="edit_news"),


    path('upload_news_by_classwise/<str:dept_id>/', views.upload_news_by_department, name='upload_news_by_department'),
    path('news/<str:dept_id>/', views.post_news_page, name='post_news_page'),
    path('news/<str:dept_id>/delete/<str:news_id>/', views.delete_department_news, name='delete_department_news'),
    path('news/<str:dept_id>/delete-all/', views.delete_all_department_news, name='delete_all_news'),
    path('department/<str:dept_id>/news/edit/<str:news_id>/', views.edit_department_news, name='edit_department_news'),

    path('post-videos/', views.post_videos, name='post_videos'),
    path('edit_video/<str:video_id>/', views.edit_video, name='edit_video'),
    path('delete_video/<str:video_id>/', views.delete_video, name='delete_video'),


     
    #LeaderBoard
    path('leaderboard/', views.leaderboard_view, name='leaderboard'),




     #Coding Questions
    path('post-questions/', views.post_questions, name='post_questions'),
    path('post_questions/background/', views.question_background, name='question_background'),
    path('post_questions/details/', views.question_details, name='question_details'),
    path('post_questions/solution/', views.question_solution, name='question_solution'),
    path('post_questions/testcases/', views.question_testcases, name='question_testcases'),
    path('post_questions/submit/', views.submit_question, name='submit_question'),
    path('posted_questions/', views.posted_questions, name='posted_questions'),
    path('posted_questions/delete/<str:question_id>/', views.delete_question, name='delete_question'),

    path("post-css-problem/", views.post_css_problem, name="post_css_problem"),
    #Discussions
    path('discussions/', views.discussions, name='discussions'),
    path('certifications/', views.certifications_view, name='certifications'),
     

     #Logout
    path('logout/', views.logout_view, name='logout'),



]
