from django.urls import path

# 注意這裡要修改成自己的 views
from app_user_keyword_association_db import views

app_name="app_user_keyword_association_db"

urlpatterns = [

    path('', views.home, name='home'),
    path('api_get_userkey_associate/', views.api_get_userkey_associate),

]
