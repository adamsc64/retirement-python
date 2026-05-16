from django.contrib import admin

from .models import Account, ImportBatch, RawTransaction, Transaction


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ["institution", "name", "account_identifier", "account_type", "currency"]
    list_filter = ["institution", "account_type", "currency"]
    search_fields = ["institution", "name", "account_identifier"]


@admin.register(ImportBatch)
class ImportBatchAdmin(admin.ModelAdmin):
    list_display = [
        "source_file",
        "source_institution",
        "source_profile",
        "account",
        "imported_at",
        "row_count",
        "file_hash",
    ]
    list_filter = ["source_institution", "source_profile"]
    search_fields = ["source_file", "source_institution", "source_profile", "file_hash"]
    readonly_fields = ["imported_at", "file_hash"]


@admin.register(RawTransaction)
class RawTransactionAdmin(admin.ModelAdmin):
    list_display = ["import_batch", "row_number"]
    list_filter = ["import_batch__source_institution"]
    search_fields = ["import_batch__source_file"]
    raw_id_fields = ["import_batch"]


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = [
        "posted_date",
        "description_raw",
        "amount",
        "currency",
        "direction",
        "account",
        "source_institution",
    ]
    list_filter = ["source_institution", "currency", "direction", "posted_date"]
    search_fields = [
        "description_raw",
        "description_clean",
        "source_row_key",
        "event_fingerprint",
        "source_native_id",
        "source_file",
    ]
    readonly_fields = ["created_at", "updated_at", "source_row_key", "event_fingerprint"]
    raw_id_fields = ["import_batch", "raw_transaction", "account"]
    date_hierarchy = "posted_date"
