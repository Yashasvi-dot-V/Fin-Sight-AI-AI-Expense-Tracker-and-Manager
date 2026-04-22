from django.urls import path
from . import views
from .models import Expense

urlpatterns = [
    path('', views.index, name='index'),
    path("login/", views.login_view, name="login"),
    path("signup/", views.signup_view, name="signup"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("analytics/", views.analytics_dashboard, name="analytics"),
    path("add-expense/", views.add_expense_view, name="add_expense"),
    path("delete-expense/<int:id>/", views.delete_expense_view, name="delete_expense"),
    path("edit-expense/<int:id>/", views.edit_expense_view, name="edit_expense"),
    path("scan-receipt/",views.scan_receipt_view,name="scan_receipt"),
    path("logout/", views.logout_view, name="logout")
]
