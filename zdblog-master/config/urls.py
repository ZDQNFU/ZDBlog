"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.urls import path, include
from article.views.s_views import ImageUploadView

urlpatterns = [
    path('admin/', admin.site.urls),

    path(
        'api/articles/',
        include('article.urls')
    ),

    path(
        'api/auth/',
        include('user.urls')
    ),
    path(
        'api/links/',
        include('link.urls')
    ),
    path(
        'api/chat-robot/',
        include('chat_robot.urls')
    ),
    path(
        'api/tracking/',
        include('tracking_api.urls')
    ),
    path(
        'api/messages/',
        include('message.urls')
    ),
    path('api/moments/', include('moment.urls')),
    path(
        'api/system-config/',
        include('system_config.urls')
    ),
    path(
        'api/articles/s/upload-image/',
        ImageUploadView.as_view(),
        name='s_image_upload'
    ),
]
