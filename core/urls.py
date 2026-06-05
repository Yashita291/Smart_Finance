from django.urls import path
from django.contrib.auth import views as auth_views
from rest_framework.routers import DefaultRouter
from core import views, api

router = DefaultRouter()
router.register("expenses", api.ExpenseViewSet)
router.register("income", api.IncomeViewSet)
router.register("budgets", api.BudgetViewSet)
router.register("goals", api.SavingsGoalViewSet)
router.register("bills", api.BillReminderViewSet)
router.register("notifications", api.NotificationViewSet)

urlpatterns = [
    path("", views.landing, name="landing"),
    path("register/", views.register, name="register"),
    path("login/", auth_views.LoginView.as_view(template_name="registration/login.html"), name="login"),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),

    # Password change/reset (Django built-ins)
    path("password_change/", auth_views.PasswordChangeView.as_view(
        template_name="registration/password_change.html"), name="password_change"),
    path("password_change/done/", auth_views.PasswordChangeDoneView.as_view(
        template_name="registration/password_change_done.html"), name="password_change_done"),
    path("password_reset/", auth_views.PasswordResetView.as_view(
        template_name="registration/password_reset.html"), name="password_reset"),
    path("password_reset/done/", auth_views.PasswordResetDoneView.as_view(
        template_name="registration/password_reset_done.html"), name="password_reset_done"),
    path("reset/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="registration/password_reset_confirm.html"), name="password_reset_confirm"),
    path("reset/done/", auth_views.PasswordResetCompleteView.as_view(
        template_name="registration/password_reset_complete.html"), name="password_reset_complete"),

    path("dashboard/", views.dashboard, name="dashboard"),
    path("chart-data/", views.chart_data, name="chart_data"),

    path("expenses/", views.expense_list, name="expense_list"),
    path("expenses/add/", views.expense_create, name="expense_create"),
    path("expenses/<int:pk>/edit/", views.expense_edit, name="expense_edit"),
    path("expenses/<int:pk>/delete/", views.expense_delete, name="expense_delete"),

    path("income/", views.income_list, name="income_list"),
    path("income/add/", views.income_create, name="income_create"),
    path("income/<int:pk>/edit/", views.income_edit, name="income_edit"),
    path("income/<int:pk>/delete/", views.income_delete, name="income_delete"),

    path("budgets/", views.budget_list, name="budget_list"),
    path("budgets/add/", views.budget_create, name="budget_create"),
    path("budgets/<int:pk>/delete/", views.budget_delete, name="budget_delete"),

    path("goals/", views.goal_list, name="goal_list"),
    path("goals/add/", views.goal_create, name="goal_create"),
    path("goals/<int:pk>/delete/", views.goal_delete, name="goal_delete"),

    path("bills/", views.bill_list, name="bill_list"),
    path("bills/add/", views.bill_create, name="bill_create"),
    path("bills/<int:pk>/delete/", views.bill_delete, name="bill_delete"),

    path("analytics/", views.analytics, name="analytics"),
    path("insights/", views.insights, name="insights"),
    path("reports/", views.reports, name="reports"),
    path("reports/export/csv/", views.export_csv, name="export_csv"),
    path("reports/export/excel/", views.export_excel, name="export_excel"),
    path("reports/export/pdf/", views.export_pdf, name="export_pdf"),
]

api_urlpatterns = router.urls
