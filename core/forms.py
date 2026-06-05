from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from core.models import Expense, Income, Budget, SavingsGoal, BillReminder


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in self.fields.values():
            f.widget.attrs["class"] = (f.widget.attrs.get("class", "") + " form-control").strip()

    def clean_email(self):
        email = self.cleaned_data["email"]
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email


def _style(fields):
    """Apply Bootstrap classes without repeating widget attrs everywhere."""
    for f in fields.values():
        existing = f.widget.attrs.get("class", "")
        if isinstance(f.widget, (forms.CheckboxInput,)):
            f.widget.attrs["class"] = (existing + " form-check-input").strip()
        elif isinstance(f.widget, forms.Select):
            f.widget.attrs["class"] = (existing + " form-select").strip()
        else:
            f.widget.attrs["class"] = (existing + " form-control").strip()


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ["title", "amount", "category", "date", "payment_method", "notes", "receipt"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = self.fields["category"].queryset.filter(kind="expense")
        _style(self.fields)


class IncomeForm(forms.ModelForm):
    class Meta:
        model = Income
        fields = ["source", "amount", "date", "notes"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class BudgetForm(forms.ModelForm):
    class Meta:
        model = Budget
        fields = ["category", "month", "limit_amount"]
        widgets = {"month": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = self.fields["category"].queryset.filter(kind="expense")
        _style(self.fields)


class SavingsGoalForm(forms.ModelForm):
    class Meta:
        model = SavingsGoal
        fields = ["name", "target_amount", "current_amount", "deadline"]
        widgets = {"deadline": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)


class BillReminderForm(forms.ModelForm):
    class Meta:
        model = BillReminder
        fields = ["name", "amount", "due_date", "frequency", "is_active"]
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _style(self.fields)
