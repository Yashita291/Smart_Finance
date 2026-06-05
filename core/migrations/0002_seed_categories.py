from django.db import migrations

EXPENSE_CATS = [
    ("Food", "fa-utensils"), ("Rent", "fa-house"), ("Transport", "fa-car"),
    ("Shopping", "fa-bag-shopping"), ("Education", "fa-graduation-cap"),
    ("Healthcare", "fa-heart-pulse"), ("Entertainment", "fa-film"),
    ("Utilities", "fa-bolt"), ("Investment", "fa-chart-line"), ("Other", "fa-ellipsis"),
]
INCOME_CATS = [
    ("Salary", "fa-money-bill"), ("Freelancing", "fa-laptop"),
    ("Business", "fa-briefcase"), ("Investments", "fa-chart-line"), ("Other", "fa-ellipsis"),
]


def seed(apps, schema_editor):
    Category = apps.get_model("core", "Category")
    for name, icon in EXPENSE_CATS:
        Category.objects.get_or_create(name=name, kind="expense", defaults={"icon": icon})
    for name, icon in INCOME_CATS:
        Category.objects.get_or_create(name=name, kind="income", defaults={"icon": icon})


def unseed(apps, schema_editor):
    Category = apps.get_model("core", "Category")
    Category.objects.all().delete()


class Migration(migrations.Migration):
    dependencies = [("core", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]
