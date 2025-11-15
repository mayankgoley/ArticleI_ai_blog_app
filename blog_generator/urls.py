from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login', views.user_login, name='login'),
    path('signup', views.user_signup, name='signup'),
    path('logout', views.user_logout, name='logout'),
    path('all-blogs', views.all_blogs, name='all-blogs'),
    path('blog-details/<int:pk>/', views.blog_details, name='blog-details'),
    path('generate-blog', views.generate_blog, name='generate-blog'),
    path('download-blog/<int:pk>/', views.download_blog, name='download-blog'),
    path('delete-blog/<int:pk>/', views.delete_blog, name='delete-blog'),
    path('enhance-content', views.enhance_content, name='enhance-content'),
]