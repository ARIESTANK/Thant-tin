from django.urls import path
from dashboard_app import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("api/dashboard/", views.dashboard_api, name="dashboard_api"),
    path("api/predict/", views.predict_enrollment, name="predict_enrollment"),
]
