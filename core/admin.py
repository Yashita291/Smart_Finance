from django.contrib import admin
from core.models import (
    Category, Expense, Income, Budget, SavingsGoal,
    BillReminder, Notification, AIInsight,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "kind", "icon")
    list_filter = ("kind",)


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ("title", "user", "amount", "category", "date", "payment_method")
    list_filter = ("category", "payment_method", "date")
    search_fields = ("title", "notes")
    date_hierarchy = "date"


@admin.register(Income)
class IncomeAdmin(admin.ModelAdmin):
    list_display = ("source", "user", "amount", "date")
    list_filter = ("source", "date")


@admin.register(Budget)
class BudgetAdmin(admin.ModelAdmin):
    list_display = ("user", "category", "month", "limit_amount")
    list_filter = ("month",)


@admin.register(SavingsGoal)
class SavingsGoalAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "target_amount", "current_amount", "deadline")


@admin.register(BillReminder)
class BillReminderAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "amount", "due_date", "frequency", "is_active")
    list_filter = ("frequency", "is_active")


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("user", "message", "is_read", "created_at")
    list_filter = ("is_read",)


@admin.register(AIInsight)
class AIInsightAdmin(admin.ModelAdmin):
    list_display = ("user", "text", "source", "created_at")
    list_filter = ("source",)
