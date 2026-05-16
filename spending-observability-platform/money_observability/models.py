from django.db import models


class Currency(models.TextChoices):
    USD = "USD", "US Dollar"
    GBP = "GBP", "British Pound"
    EUR = "EUR", "Euro"


class AccountType(models.TextChoices):
    CHECKING = "checking", "Checking"
    SAVINGS = "savings", "Savings"
    CREDIT_CARD = "credit_card", "Credit Card"
    OTHER = "other", "Other"


class Direction(models.TextChoices):
    DEBIT = "debit", "Debit"
    CREDIT = "credit", "Credit"


class Account(models.Model):
    institution = models.CharField(max_length=100)
    name = models.CharField(max_length=200)
    account_identifier = models.CharField(max_length=100)
    account_type = models.CharField(max_length=50, choices=AccountType.choices, default=AccountType.OTHER)
    currency = models.CharField(max_length=3, choices=Currency.choices, default=Currency.USD)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.institution} – {self.name} ({self.account_identifier})"

    class Meta:
        ordering = ["institution", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["institution", "account_identifier"],
                name="uniq_account_institution_identifier",
            )
        ]


class ImportBatch(models.Model):
    account = models.ForeignKey(
        Account,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="import_batches",
    )
    source_file = models.CharField(max_length=500)
    source_institution = models.CharField(max_length=100)
    source_profile = models.CharField(max_length=100, blank=True, default="")
    imported_at = models.DateTimeField(auto_now_add=True)
    file_hash = models.CharField(max_length=64, unique=True)
    row_count = models.IntegerField(default=0)

    def __str__(self) -> str:
        return f"{self.source_file} @ {self.imported_at:%Y-%m-%d %H:%M}"

    class Meta:
        ordering = ["-imported_at"]
        verbose_name_plural = "import batches"


class RawTransaction(models.Model):
    import_batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.CASCADE,
        related_name="raw_transactions",
    )
    row_number = models.IntegerField()
    raw_json = models.JSONField()

    def __str__(self) -> str:
        return f"Row {self.row_number} of {self.import_batch}"

    class Meta:
        ordering = ["import_batch", "row_number"]
        unique_together = [("import_batch", "row_number")]


class Transaction(models.Model):
    source_row_key = models.CharField(max_length=64, unique=True)
    event_fingerprint = models.CharField(max_length=64, db_index=True, blank=True, default="")
    source_native_id = models.CharField(max_length=200, db_index=True, blank=True, default="")
    import_batch = models.ForeignKey(
        ImportBatch,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    raw_transaction = models.OneToOneField(
        RawTransaction,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="transaction",
    )
    account = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name="transactions",
    )
    source_file = models.CharField(max_length=500)
    source_institution = models.CharField(max_length=100)
    posted_date = models.DateField()
    transaction_date = models.DateField(null=True, blank=True)
    description_raw = models.TextField()
    description_clean = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, choices=Currency.choices)
    original_amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    original_currency = models.CharField(max_length=3, choices=Currency.choices, blank=True)
    direction = models.CharField(max_length=10, choices=Direction.choices)
    excluded = models.BooleanField(default=False, db_index=True)
    exclusion_reason = models.CharField(max_length=100, blank=True, default="")
    exclusion_rule_id = models.CharField(max_length=100, blank=True, default="")
    excluded_at = models.DateTimeField(null=True, blank=True)
    category = models.CharField(max_length=100, blank=True, default="", db_index=True)
    category_rule_id = models.CharField(max_length=100, blank=True, default="")
    categorized_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.posted_date} {self.description_raw[:60]} {self.amount} {self.currency}"

    class Meta:
        ordering = ["-posted_date", "description_raw"]
