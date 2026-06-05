import csv
from datetime import date
from decimal import Decimal
from io import BytesIO

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.views import LoginView
from django.core.paginator import Paginator
from django.db.models import Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from core.forms import (
    RegisterForm, ExpenseForm, IncomeForm, BudgetForm,
    SavingsGoalForm, BillReminderForm,
)
from core.models import (
    Expense, Income, Budget, SavingsGoal, BillReminder, AIInsight,
)
from core.services.insights import refresh_insights


# ---------- Public / auth ----------

def landing(request):
    if request.user.is_authenticated:
        return redirect("dashboard")
    return render(request, "landing.html")


def register(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Welcome to SmartFinance.")
            return redirect("dashboard")
    else:
        form = RegisterForm()
    return render(request, "registration/register.html", {"form": form})


# ---------- Dashboard ----------

def _month_range(d):
    start = d.replace(day=1)
    nxt = start.replace(year=start.year + 1, month=1) if start.month == 12 \
        else start.replace(month=start.month + 1)
    return start, nxt


@login_required
def dashboard(request):
    u = request.user
    today = timezone.now().date()
    m_start, m_end = _month_range(today)

    income = Income.objects.filter(user=u, date__gte=m_start, date__lt=m_end).aggregate(
        t=Sum("amount"))["t"] or Decimal("0")
    expense = Expense.objects.filter(user=u, date__gte=m_start, date__lt=m_end).aggregate(
        t=Sum("amount"))["t"] or Decimal("0")
    balance = income - expense

    budget_total = Budget.objects.filter(user=u, month=m_start).aggregate(
        t=Sum("limit_amount"))["t"] or Decimal("0")
    budget_util = round((expense / budget_total) * 100, 1) if budget_total else 0

    recent = list(Expense.objects.filter(user=u).select_related("category")[:10])

    upcoming_bills = BillReminder.objects.filter(
        user=u, is_active=True, due_date__gte=today).order_by("due_date")[:5]

    ctx = {
        "income": income, "expense": expense, "balance": balance,
        "budget_total": budget_total, "budget_util": budget_util,
        "recent": recent, "upcoming_bills": upcoming_bills,
        "month_label": m_start.strftime("%B %Y"),
    }
    return render(request, "dashboard.html", ctx)


# ---------- Chart data (JSON, consumed by Chart.js) ----------

@login_required
def chart_data(request):
    u = request.user
    today = timezone.now().date()

    # Last 6 months of income vs expense
    labels, inc_series, exp_series = [], [], []
    cursor = today.replace(day=1)
    months = []
    for _ in range(6):
        months.append(cursor)
        cursor = cursor.replace(year=cursor.year - 1, month=12) if cursor.month == 1 \
            else cursor.replace(month=cursor.month - 1)
    for m in reversed(months):
        m_start, m_end = _month_range(m)
        labels.append(m.strftime("%b %y"))
        inc_series.append(float(Income.objects.filter(
            user=u, date__gte=m_start, date__lt=m_end).aggregate(t=Sum("amount"))["t"] or 0))
        exp_series.append(float(Expense.objects.filter(
            user=u, date__gte=m_start, date__lt=m_end).aggregate(t=Sum("amount"))["t"] or 0))

    # Category breakdown, current month
    m_start, m_end = _month_range(today)
    cat_rows = (Expense.objects.filter(user=u, date__gte=m_start, date__lt=m_end)
                .values("category__name").annotate(t=Sum("amount")).order_by("-t"))
    cat_labels = [r["category__name"] for r in cat_rows]
    cat_values = [float(r["t"]) for r in cat_rows]

    # Budget vs actual, current month
    budgets = Budget.objects.filter(user=u, month=m_start).select_related("category")
    b_labels = [b.category.name for b in budgets]
    b_limit = [float(b.limit_amount) for b in budgets]
    b_spent = [float(b.spent()) for b in budgets]

    return JsonResponse({
        "trend": {"labels": labels, "income": inc_series, "expense": exp_series},
        "category": {"labels": cat_labels, "values": cat_values},
        "budget": {"labels": b_labels, "limit": b_limit, "spent": b_spent},
    })


# ---------- Expenses ----------

@login_required
def expense_list(request):
    qs = Expense.objects.filter(user=request.user).select_related("category")
    q = request.GET.get("q", "").strip()
    cat = request.GET.get("category", "")
    start = request.GET.get("start", "")
    end = request.GET.get("end", "")
    if q:
        qs = qs.filter(title__icontains=q)
    if cat:
        qs = qs.filter(category_id=cat)
    if start:
        qs = qs.filter(date__gte=start)
    if end:
        qs = qs.filter(date__lte=end)

    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get("page"))
    from core.models import Category
    cats = Category.objects.filter(kind="expense")
    return render(request, "expense_list.html", {
        "page": page, "categories": cats,
        "q": q, "sel_cat": cat, "start": start, "end": end,
    })


@login_required
def expense_create(request):
    form = ExpenseForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        obj.save()
        refresh_insights(request.user)
        messages.success(request, "Expense added.")
        return redirect("expense_list")
    return render(request, "form.html", {"form": form, "title": "Add Expense"})


@login_required
def expense_edit(request, pk):
    obj = get_object_or_404(Expense, pk=pk, user=request.user)
    form = ExpenseForm(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        refresh_insights(request.user)
        messages.success(request, "Expense updated.")
        return redirect("expense_list")
    return render(request, "form.html", {"form": form, "title": "Edit Expense"})


@login_required
def expense_delete(request, pk):
    obj = get_object_or_404(Expense, pk=pk, user=request.user)
    if request.method == "POST":
        obj.delete()
        refresh_insights(request.user)
        messages.success(request, "Expense deleted.")
        return redirect("expense_list")
    return render(request, "confirm_delete.html", {"obj": obj, "kind": "expense"})


# ---------- Income ----------

@login_required
def income_list(request):
    qs = Income.objects.filter(user=request.user)
    src = request.GET.get("source", "")
    if src:
        qs = qs.filter(source=src)
    paginator = Paginator(qs, 20)
    page = paginator.get_page(request.GET.get("page"))
    return render(request, "income_list.html", {
        "page": page, "sources": Income.SOURCE_CHOICES, "sel_src": src})


@login_required
def income_create(request):
    form = IncomeForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        obj.save()
        messages.success(request, "Income added.")
        return redirect("income_list")
    return render(request, "form.html", {"form": form, "title": "Add Income"})


@login_required
def income_edit(request, pk):
    obj = get_object_or_404(Income, pk=pk, user=request.user)
    form = IncomeForm(request.POST or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Income updated.")
        return redirect("income_list")
    return render(request, "form.html", {"form": form, "title": "Edit Income"})


@login_required
def income_delete(request, pk):
    obj = get_object_or_404(Income, pk=pk, user=request.user)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Income deleted.")
        return redirect("income_list")
    return render(request, "confirm_delete.html", {"obj": obj, "kind": "income"})


# ---------- Budgets ----------

@login_required
def budget_list(request):
    today = timezone.now().date().replace(day=1)
    budgets = Budget.objects.filter(user=request.user, month=today).select_related("category")
    return render(request, "budget_list.html", {"budgets": budgets, "month": today})


@login_required
def budget_create(request):
    form = BudgetForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        obj.month = obj.month.replace(day=1)
        try:
            obj.save()
            messages.success(request, "Budget created.")
            return redirect("budget_list")
        except Exception:
            messages.error(request, "A budget for that category and month already exists.")
    return render(request, "form.html", {"form": form, "title": "Create Budget"})


@login_required
def budget_delete(request, pk):
    obj = get_object_or_404(Budget, pk=pk, user=request.user)
    if request.method == "POST":
        obj.delete()
        messages.success(request, "Budget deleted.")
        return redirect("budget_list")
    return render(request, "confirm_delete.html", {"obj": obj, "kind": "budget"})


# ---------- Savings goals ----------

@login_required
def goal_list(request):
    goals = SavingsGoal.objects.filter(user=request.user)
    return render(request, "goal_list.html", {"goals": goals})


@login_required
def goal_create(request):
    form = SavingsGoalForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        obj.save()
        messages.success(request, "Goal created.")
        return redirect("goal_list")
    return render(request, "form.html", {"form": form, "title": "Add Savings Goal"})


@login_required
def goal_delete(request, pk):
    obj = get_object_or_404(SavingsGoal, pk=pk, user=request.user)
    if request.method == "POST":
        obj.delete()
        return redirect("goal_list")
    return render(request, "confirm_delete.html", {"obj": obj, "kind": "goal"})


# ---------- Bills ----------

@login_required
def bill_list(request):
    bills = BillReminder.objects.filter(user=request.user)
    return render(request, "bill_list.html", {"bills": bills})


@login_required
def bill_create(request):
    form = BillReminderForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        obj = form.save(commit=False)
        obj.user = request.user
        obj.save()
        messages.success(request, "Bill reminder added.")
        return redirect("bill_list")
    return render(request, "form.html", {"form": form, "title": "Add Bill Reminder"})


@login_required
def bill_delete(request, pk):
    obj = get_object_or_404(BillReminder, pk=pk, user=request.user)
    if request.method == "POST":
        obj.delete()
        return redirect("bill_list")
    return render(request, "confirm_delete.html", {"obj": obj, "kind": "bill"})


# ---------- Analytics / Insights ----------

@login_required
def analytics(request):
    return render(request, "analytics.html")


@login_required
def insights(request):
    if request.method == "POST":
        refresh_insights(request.user)
        return redirect("insights")
    items = AIInsight.objects.filter(user=request.user)
    return render(request, "insights.html", {"items": items})


# ---------- Reports & export ----------

@login_required
def reports(request):
    u = request.user
    today = timezone.now().date()
    m_start, m_end = _month_range(today)
    income = Income.objects.filter(user=u, date__gte=m_start, date__lt=m_end).aggregate(
        t=Sum("amount"))["t"] or Decimal("0")
    expense = Expense.objects.filter(user=u, date__gte=m_start, date__lt=m_end).aggregate(
        t=Sum("amount"))["t"] or Decimal("0")
    top = (Expense.objects.filter(user=u, date__gte=m_start, date__lt=m_end)
           .values("category__name").annotate(t=Sum("amount")).order_by("-t")[:5])
    return render(request, "reports.html", {
        "income": income, "expense": expense, "savings": income - expense,
        "top": top, "month_label": m_start.strftime("%B %Y"),
    })


@login_required
def export_csv(request):
    u = request.user
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = 'attachment; filename="transactions.csv"'
    w = csv.writer(resp)
    w.writerow(["Type", "Date", "Title/Source", "Category", "Amount"])
    for e in Expense.objects.filter(user=u).select_related("category"):
        w.writerow(["Expense", e.date, e.title, e.category.name, e.amount])
    for i in Income.objects.filter(user=u):
        w.writerow(["Income", i.date, i.get_source_display(), "-", i.amount])
    return resp


@login_required
def export_excel(request):
    from openpyxl import Workbook
    u = request.user
    wb = Workbook()
    ws = wb.active
    ws.title = "Transactions"
    ws.append(["Type", "Date", "Title/Source", "Category", "Amount"])
    for e in Expense.objects.filter(user=u).select_related("category"):
        ws.append(["Expense", e.date.isoformat(), e.title, e.category.name, float(e.amount)])
    for i in Income.objects.filter(user=u):
        ws.append(["Income", i.date.isoformat(), i.get_source_display(), "-", float(i.amount)])
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    resp = HttpResponse(
        buf.read(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    resp["Content-Disposition"] = 'attachment; filename="transactions.xlsx"'
    return resp


@login_required
def export_pdf(request):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas as pdf_canvas
    u = request.user
    today = timezone.now().date()
    m_start, m_end = _month_range(today)
    income = Income.objects.filter(user=u, date__gte=m_start, date__lt=m_end).aggregate(
        t=Sum("amount"))["t"] or Decimal("0")
    expense = Expense.objects.filter(user=u, date__gte=m_start, date__lt=m_end).aggregate(
        t=Sum("amount"))["t"] or Decimal("0")

    buf = BytesIO()
    c = pdf_canvas.Canvas(buf, pagesize=A4)
    w, h = A4
    c.setFont("Helvetica-Bold", 18)
    c.drawString(50, h - 60, "SmartFinance - Monthly Report")
    c.setFont("Helvetica", 11)
    c.drawString(50, h - 90, f"User: {u.username}")
    c.drawString(50, h - 110, f"Month: {m_start:%B %Y}")
    c.drawString(50, h - 140, f"Total Income:  Rs {income:,.2f}")
    c.drawString(50, h - 160, f"Total Expense: Rs {expense:,.2f}")
    c.drawString(50, h - 180, f"Net Savings:   Rs {income - expense:,.2f}")
    c.showPage()
    c.save()
    buf.seek(0)
    resp = HttpResponse(buf.read(), content_type="application/pdf")
    resp["Content-Disposition"] = 'attachment; filename="report.pdf"'
    return resp
