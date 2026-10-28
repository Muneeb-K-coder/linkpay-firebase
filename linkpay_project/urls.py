from django.contrib import admin
from django.urls import path
from links import views

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", views.dashboard_page, name="home"),
    path("api/dashboard/", views.dashboard_api, name="dashboard_api"),
    path("api/links/", views.create_link, name="create_link"),
    path("api/withdrawals/", views.create_withdrawal, name="create_withdrawal"),
    path("api/admin/withdrawals/", views.admin_withdrawals, name="admin_withdrawals"),
    path("api/admin/withdrawals/<int:withdrawal_id>/", views.review_withdrawal, name="review_withdrawal"),
    path("s/<str:code>/", views.redirect_short_link, name="short_redirect"),
]
