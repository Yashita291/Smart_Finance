from rest_framework import viewsets
from core.models import Expense, Income, Budget, SavingsGoal, BillReminder, Notification
from core.serializers import (
    ExpenseSerializer, IncomeSerializer, BudgetSerializer,
    SavingsGoalSerializer, BillReminderSerializer, NotificationSerializer,
)


class OwnedModelViewSet(viewsets.ModelViewSet):
    """Scopes every queryset to the requesting user and stamps ownership on create.
    This is the RBAC boundary - no separate role framework needed for 2 roles."""
    def get_queryset(self):
        return self.queryset.model.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class ExpenseViewSet(OwnedModelViewSet):
    queryset = Expense.objects.all()
    serializer_class = ExpenseSerializer


class IncomeViewSet(OwnedModelViewSet):
    queryset = Income.objects.all()
    serializer_class = IncomeSerializer


class BudgetViewSet(OwnedModelViewSet):
    queryset = Budget.objects.all()
    serializer_class = BudgetSerializer


class SavingsGoalViewSet(OwnedModelViewSet):
    queryset = SavingsGoal.objects.all()
    serializer_class = SavingsGoalSerializer


class BillReminderViewSet(OwnedModelViewSet):
    queryset = BillReminder.objects.all()
    serializer_class = BillReminderSerializer


class NotificationViewSet(OwnedModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
