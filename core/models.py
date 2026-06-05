from decimal import Decimal
from django.conf import settings
from django.db import models
from django.utils import timezone


class Category(models.Model):
    """Expense/income categories. Admin-managed; default set seeded via migration."""
    KIND_EXPENSE = "expense"
    KIND_INCOME = "income"
    KIND_CHOICES = [(KIND_EXPENSE, "Expense"), (KIND_INCOME, "Income")]

    name = models.CharField(max_length=64)
    kind = models.CharField(max_length=10, choices=KIND_CHOICES, default=KIND_EXPENSE)
    icon = models.CharField(max_length=40, blank=True, help_text="Font Awesome class, e.g. 'fa-utensils'")

    class Meta:
        verbose_name_plural = "categories"
        unique_together = ("name", "kind")
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.kind})"


class Expense(models.Model):
    PAYMENT_CHOICES = [
        ("cash", "Cash"), ("card", "Card"), ("upi", "UPI"),
        ("netbanking", "Net Banking"), ("other", "Other"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="expenses")
    title = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="expenses")
    date = models.DateField(default=timezone.now)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default="upi")
    notes = models.TextField(blank=True)
    receipt = models.ImageField(upload_to="receipts/%Y/%m/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [
            models.Index(fields=["user", "-date"]),
            models.Index(fields=["user", "category"]),
        ]

    def __str__(self):
        return f"{self.title} - {self.amount}"


class Income(models.Model):
    SOURCE_CHOICES = [
        ("salary", "Salary"), ("freelancing", "Freelancing"), ("business", "Business"),
        ("investments", "Investments"), ("other", "Other"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="incomes")
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="salary")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-created_at"]
        indexes = [models.Index(fields=["user", "-date"])]

    def __str__(self):
        return f"{self.get_source_display()} - {self.amount}"


class Budget(models.Model):
    """Per-category monthly budget. 'month' stored as first day of the month."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="budgets")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="budgets")
    month = models.DateField(help_text="First day of the budget month")
    limit_amount = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        unique_together = ("user", "category", "month")
        ordering = ["-month"]
        indexes = [models.Index(fields=["user", "month"])]

    def spent(self):
        agg = Expense.objects.filter(
            user=self.user, category=self.category,
            date__year=self.month.year, date__month=self.month.month,
        ).aggregate(total=models.Sum("amount"))
        return agg["total"] or Decimal("0")

    def remaining(self):
        return self.limit_amount - self.spent()

    def percent_used(self):
        if self.limit_amount == 0:
            return 0
        return round((self.spent() / self.limit_amount) * 100, 1)

    def __str__(self):
        return f"{self.category.name} {self.month:%b %Y} = {self.limit_amount}"


class SavingsGoal(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="goals")
    name = models.CharField(max_length=120)
    target_amount = models.DecimalField(max_digits=12, decimal_places=2)
    current_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0"))
    deadline = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["deadline", "name"]

    def percent(self):
        if self.target_amount == 0:
            return 0
        return min(round((self.current_amount / self.target_amount) * 100, 1), 100)

    def __str__(self):
        return f"{self.name} ({self.percent()}%)"


class BillReminder(models.Model):
    FREQ_CHOICES = [
        ("weekly", "Weekly"), ("monthly", "Monthly"),
        ("quarterly", "Quarterly"), ("yearly", "Yearly"),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bills")
    name = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    due_date = models.DateField()
    frequency = models.CharField(max_length=12, choices=FREQ_CHOICES, default="monthly")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["due_date"]
        indexes = [models.Index(fields=["user", "due_date"])]

    def __str__(self):
        return f"{self.name} due {self.due_date}"


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.message[:50]


class AIInsight(models.Model):
    """
    Generated insights. `source` distinguishes deterministic rules from LLM output.
    The LLM path is a swappable stub (core/services/insights.py) - no vendor hardcoded.
    """
    SOURCE_RULE = "rule"
    SOURCE_LLM = "llm"
    SOURCE_CHOICES = [(SOURCE_RULE, "Rule engine"), (SOURCE_LLM, "LLM")]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="insights")
    text = models.TextField()
    source = models.CharField(max_length=8, choices=SOURCE_CHOICES, default=SOURCE_RULE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.text[:60]
