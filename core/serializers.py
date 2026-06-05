from rest_framework import serializers
from core.models import Expense, Income, Budget, SavingsGoal, BillReminder, Notification


class ExpenseSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Expense
        fields = ["id", "title", "amount", "category", "category_name",
                  "date", "payment_method", "notes"]


class IncomeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Income
        fields = ["id", "source", "amount", "date", "notes"]


class BudgetSerializer(serializers.ModelSerializer):
    spent = serializers.SerializerMethodField()
    remaining = serializers.SerializerMethodField()

    class Meta:
        model = Budget
        fields = ["id", "category", "month", "limit_amount", "spent", "remaining"]

    def get_spent(self, obj):
        return obj.spent()

    def get_remaining(self, obj):
        return obj.remaining()


class SavingsGoalSerializer(serializers.ModelSerializer):
    percent = serializers.SerializerMethodField()

    class Meta:
        model = SavingsGoal
        fields = ["id", "name", "target_amount", "current_amount", "deadline", "percent"]

    def get_percent(self, obj):
        return obj.percent()


class BillReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillReminder
        fields = ["id", "name", "amount", "due_date", "frequency", "is_active"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "message", "is_read", "created_at"]
