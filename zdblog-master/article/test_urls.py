from django.urls import include, path

urlpatterns = [
    path('api/articles/', include('article.urls')),
    path('api/system-config/', include('system_config.urls')),
]
