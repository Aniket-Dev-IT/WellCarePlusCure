from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone

from .models import Payment, Transaction, Invoice, PaymentMethod


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """
    Admin interface for Payment model.
    """
    list_display = [
        'payment_reference', 'patient_name', 'doctor_name', 
        'amount_display', 'status', 'payment_type', 'created_at'
    ]
    list_filter = [
        'status', 'payment_type', 'currency', 'created_at',
        ('paid_at', admin.DateFieldListFilter)
    ]
    search_fields = [
        'payment_reference', 'patient__username', 'patient__email',
        'doctor__first_name', 'doctor__last_name', 'description'
    ]
    readonly_fields = [
        'id', 'payment_reference', 'stripe_payment_intent_id',
        'stripe_charge_id', 'created_at', 'updated_at', 'paid_at'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'payment_reference', 'appointment', 'patient', 'doctor')
        }),
        ('Payment Details', {
            'fields': ('payment_type', 'amount', 'currency', 'status', 'description')
        }),
        ('Stripe Integration', {
            'fields': ('stripe_payment_intent_id', 'stripe_payment_method_id', 'stripe_charge_id'),
            'classes': ('collapse',)
        }),
        ('Contact & Receipt', {
            'fields': ('receipt_email', 'payment_method'),
            'classes': ('collapse',)
        }),
        ('Refund Information', {
            'fields': ('refund_amount', 'refund_reason'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at', 'paid_at'),
            'classes': ('collapse',)
        })
    )
    
    def patient_name(self, obj):
        """Display patient name with link to user admin."""
        url = reverse('admin:auth_user_change', args=[obj.patient.id])
        return format_html('<a href="{}">{}</a>', url, obj.patient.get_full_name() or obj.patient.username)
    patient_name.short_description = 'Patient'
    
    def doctor_name(self, obj):
        """Display doctor name with link to doctor admin."""
        url = reverse('admin:doctors_doctor_change', args=[obj.doctor.id])
        return format_html('<a href="{}">{}</a>', url, obj.doctor.display_name)
    doctor_name.short_description = 'Doctor'
    
    def amount_display(self, obj):
        """Display amount with currency and refund info."""
        display = f"{obj.amount} {obj.currency}"
        if obj.refund_amount > 0:
            display += f" (Refunded: {obj.refund_amount})"
        return display
    amount_display.short_description = 'Amount'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('patient', 'doctor', 'appointment')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """
    Admin interface for Transaction model.
    """
    list_display = [
        'transaction_id', 'payment_reference', 'transaction_type',
        'amount_display', 'processed_at'
    ]
    list_filter = [
        'transaction_type', 'currency', 'processed_at'
    ]
    search_fields = [
        'transaction_id', 'payment__payment_reference',
        'external_reference', 'description'
    ]
    readonly_fields = [
        'id', 'transaction_id', 'created_at', 'processed_at'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'transaction_id', 'payment', 'transaction_type')
        }),
        ('Amount Details', {
            'fields': ('amount', 'currency', 'description')
        }),
        ('External References', {
            'fields': ('external_reference', 'metadata'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'processed_at'),
            'classes': ('collapse',)
        })
    )
    
    def payment_reference(self, obj):
        """Display payment reference with link."""
        url = reverse('admin:payments_payment_change', args=[obj.payment.id])
        return format_html('<a href="{}">{}</a>', url, obj.payment.payment_reference)
    payment_reference.short_description = 'Payment'
    
    def amount_display(self, obj):
        """Display amount with currency and sign for refunds."""
        sign = "-" if obj.amount < 0 else ""
        return f"{sign}{abs(obj.amount)} {obj.currency}"
    amount_display.short_description = 'Amount'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('payment')


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    """
    Admin interface for Invoice model.
    """
    list_display = [
        'invoice_number', 'patient_name_display', 'doctor_name_display',
        'total_amount_display', 'status', 'issue_date', 'due_date'
    ]
    list_filter = [
        'status', 'currency', 'issue_date', 'due_date',
        ('paid_date', admin.DateFieldListFilter)
    ]
    search_fields = [
        'invoice_number', 'patient_name', 'patient_email',
        'doctor_name', 'notes'
    ]
    readonly_fields = [
        'id', 'invoice_number', 'total_amount', 'created_at', 'updated_at',
        'is_overdue', 'days_until_due'
    ]
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'invoice_number', 'appointment', 'payment')
        }),
        ('Contact Details', {
            'fields': ('patient_name', 'patient_email', 'doctor_name')
        }),
        ('Financial Details', {
            'fields': ('subtotal', 'tax_amount', 'discount_amount', 'total_amount', 'currency')
        }),
        ('Status & Dates', {
            'fields': ('status', 'issue_date', 'due_date', 'paid_date', 'is_overdue', 'days_until_due')
        }),
        ('Additional Information', {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def patient_name_display(self, obj):
        """Display patient name with email."""
        return f"{obj.patient_name} ({obj.patient_email})"
    patient_name_display.short_description = 'Patient'
    
    def doctor_name_display(self, obj):
        """Display doctor name."""
        return obj.doctor_name
    doctor_name_display.short_description = 'Doctor'
    
    def total_amount_display(self, obj):
        """Display total amount with currency."""
        return f"{obj.total_amount} {obj.currency}"
    total_amount_display.short_description = 'Total Amount'
    
    def is_overdue(self, obj):
        """Display if invoice is overdue."""
        return obj.is_overdue
    is_overdue.boolean = True
    is_overdue.short_description = 'Overdue'
    
    def days_until_due(self, obj):
        """Display days until due."""
        return obj.days_until_due
    days_until_due.short_description = 'Days Until Due'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('appointment', 'payment')


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """
    Admin interface for PaymentMethod model.
    """
    list_display = [
        'user_display', 'payment_method_display', 'is_default',
        'is_active', 'created_at'
    ]
    list_filter = [
        'payment_method_type', 'brand', 'is_default', 'is_active',
        'created_at'
    ]
    search_fields = [
        'user__username', 'user__email', 'brand', 'last_four',
        'stripe_payment_method_id'
    ]
    readonly_fields = [
        'stripe_payment_method_id', 'created_at', 'updated_at'
    ]
    fieldsets = (
        ('User Information', {
            'fields': ('user',)
        }),
        ('Payment Method Details', {
            'fields': ('payment_method_type', 'brand', 'last_four', 'exp_month', 'exp_year')
        }),
        ('Stripe Integration', {
            'fields': ('stripe_payment_method_id',),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('is_default', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def user_display(self, obj):
        """Display user with link to user admin."""
        url = reverse('admin:auth_user_change', args=[obj.user.id])
        return format_html('<a href="{}">{}</a>', url, obj.user.get_full_name() or obj.user.username)
    user_display.short_description = 'User'
    
    def payment_method_display(self, obj):
        """Display payment method info."""
        return str(obj)
    payment_method_display.short_description = 'Payment Method'
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')
