from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', views.login_choice, name='login_choice'),
    path('login/auth/', views.custom_login, name='custom_login'),
    path('logout/', views.custom_logout, name='custom_logout'),
    path('assessments/create/', views.create_assessment, name='create_assessment'),
    path('submit/<int:assessment_id>/', views.submit_assessment, name='submit_assessment'),
    path('review/<int:submission_id>/', views.review_submission, name='review_submission'),
    path('grades/upload/', views.upload_final_grades, name='upload_final_grades'),
    path('assessments/<int:assessment_id>/delete/', views.delete_assessment, name='delete_assessment'),
    
]
