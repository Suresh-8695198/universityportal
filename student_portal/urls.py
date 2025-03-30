from django.urls import path
from . import views
from .views import html_problems, solve_html_problem, submit_solution, leetcode_problems, leetcode_problem_detail, submit_code, leaderboard, generate_certifications, download_certificate, check_and_send_certificate

urlpatterns = [
   path('login/', views.student_login, name='student_login'),  # Student login
   path('dashboard/', views.student_dashboard, name='student_dashboard'),  # Student dashboard
   path('fetch/github/', views.github_problem, name='github_problem'),
   path('scrape/problem/', views.scrape_problem, name='scrape_problem'),
   path('css-battle/', views.battle, name='css-battle'),
   path('videos/', views.videos_page, name='videos'),
   path('notes/', views.student_notes, name='student_notes'),  # Student notes
   path('html-problems/', html_problems, name='html_problems'),
   path('solve-html-problem/<int:problem_id>/', solve_html_problem, name='solve_html_problem'),
   path('submit-solution/<int:problem_id>/', submit_solution, name='submit_solution'),
   path('leetcode-problems/', leetcode_problems, name='leetcode_problems'),
   path('leetcode-problem/<str:problem_id>/', leetcode_problem_detail, name='leetcode_problem_detail'),
   path('submit-code/<str:problem_id>/', submit_code, name='submit_code'),
   path('leaderboard/', leaderboard, name='leaderboard'),
   path('certifications/', generate_certifications, name='certifications'),
   path('download-certificate/<str:student_id>/', download_certificate, name='download_certificate'),
   path('send-certificate/', check_and_send_certificate, name='send_certificate'),
   #path('scrape-css-battle/', views.scrape_css_battle, name='scrape_css_battle'),  # New URL for scraping CSS Battle path('scrape-css-battle/', scrape_css_battle, name='scrape_css_battle'),  # New URL for scraping CSS Battle
   path('problems/', views.problems, name='problems'),
   path('css-battle/<str:problem_id>/', views.css_battle, name='css_battle'),  # Load specific problems
    # Other URLs...
    path('discussions/', views.discussions, name='discussions'),
    path('discussions/common/', views.common_discussion, name='common_discussion'),
    path('discussions/interview/', views.interview_discussion, name='interview_discussion'),
    path('discussions/staff/', views.staff_discussion, name='staff_discussion'),
]

