from django.urls import path
from .views import MomentListView, MomentLikeView, MomentAdminListCreateView, MomentAdminDetailView

urlpatterns = [
    path('c/list/', MomentListView.as_view(), name='moment_list'),
    path('c/<str:pk>/like/', MomentLikeView.as_view(), name='moment_like'),
    path('s/moments/', MomentAdminListCreateView.as_view(), name='moment_admin_list'),
    path('s/moments/<str:pk>/', MomentAdminDetailView.as_view(), name='moment_admin_detail'),
]
