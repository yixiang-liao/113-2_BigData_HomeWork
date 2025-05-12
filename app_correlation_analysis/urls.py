from django.urls import path
from . import views

# declare a namespace for this APP
# the name of namespace usually is set as the app name
# We will use the namespace in the future integrated website.

# 使用app_name是讓各個APP的變數與方法名稱有區隔
# 若名稱不衝突，不使用app_name也可以
# app_name是一種namespace的概念
# 整合多個可獨立運作的APP成為一個大型專案必備知識
# 在template中如何使用?
# <a class="nav-link" href="{% url 'app_top_person:home' %}">熱門人物</a>

app_name="app_correlation_analysis"

urlpatterns = [
    # 
    path('', views.home, name='home'),
    path('api_get_corr_data/', views.api_get_corr_data),
]

