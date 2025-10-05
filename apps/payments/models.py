from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone
from django.urls import reverse
from decimal import Decimal
import uuid


class Payment(models.Model):
    """
    Model representing a payment transaction.
    
    This model stores payment details and integrates with Stripe
    for processing consultation fees and other charges.
    """
    
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('succeeded', 'Succeeded'),
        ('failed', 'Failed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('partially_refunded', 'Partially Refunded'),
    ]
    
    PAYMENT_TYPES = [
        ('consultation', 'Consultation Fee'),
        ('emergency', 'Emergency Consultation'),
        ('follow_up', 'Follow-up Appointment'),
        ('prescription', 'Prescription Fee'),
        ('report', 'Medical Report'),
        ('other', 'Other'),
    ]
    
    # Unique identifiers
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    payment_reference = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique payment reference number"
    )
    
    # Related objects
    appointment = models.ForeignKey(
        'doctors.Appointment',
        on_delete=models.CASCADE,
        related_name='payments',
        help_text="Associated appointment for this payment"
    )
    patient = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payments',
        help_text="Patient making the payment"
    )
    doctor = models.ForeignKey(
        'doctors.Doctor',
        on_delete=models.CASCADE,
        related_name='received_payments',
        help_text="Doctor receiving the payment"
    )
    
    # Payment details
    payment_type = models.CharField(
        max_length=20,
        choices=PAYMENT_TYPES,
        default='consultation',
        help_text="Type of service being paid for"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Payment amount in local currency"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Payment currency (ISO 4217 code)"
    )
    
    # Status tracking
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True
    )
    
    # Stripe integration fields
    stripe_payment_intent_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        help_text="Stripe Payment Intent ID"
    )
    stripe_payment_method_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Stripe Payment Method ID"
    )
    stripe_charge_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Stripe Charge ID"
    )
    
    # Additional details
    payment_method = models.CharField(
        max_length=50,
        blank=True,
        help_text="Payment method used (card, wallet, etc.)"
    )
    description = models.TextField(
        blank=True,
        help_text="Additional payment description"
    )
    receipt_email = models.EmailField(
        blank=True,
        help_text="Email address for receipt"
    )
    
    # Refund information
    refund_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Amount refunded"
    )
    refund_reason = models.TextField(
        blank=True,
        help_text="Reason for refund"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    paid_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when payment was completed"
    )
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        indexes = [
            models.Index(fields=['patient', 'status']),
            models.Index(fields=['doctor', 'status']),
            models.Index(fields=['status', 'created_at']),
            models.Index(fields=['appointment', 'status']),
            models.Index(fields=['stripe_payment_intent_id']),
            models.Index(fields=['payment_reference']),
        ]
    
    def __str__(self):
        return f"Payment {self.payment_reference} - {self.amount} {self.currency}"
    
    @property
    def is_successful(self):
        """Check if payment was successful."""
        return self.status == 'succeeded'
    
    @property
    def can_be_refunded(self):
        """Check if payment can be refunded."""
        if self.status != 'succeeded':
            return False
        # Check if appointment is more than 24 hours away
        if self.appointment and self.appointment.can_be_cancelled:
            return True
        return False
    
    @property
    def net_amount(self):
        """Return the net amount after refunds."""
        return self.amount - self.refund_amount
    
    def get_absolute_url(self):
        """Return the absolute URL for this payment."""
        return reverse('payments:detail', kwargs={'pk': self.pk})
    
    def save(self, *args, **kwargs):
        """Override save to generate payment reference."""
        if not self.payment_reference:
            # Generate unique payment reference
            self.payment_reference = f"PAY-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Set paid_at timestamp when status changes to succeeded
        if self.status == 'succeeded' and not self.paid_at:
            self.paid_at = timezone.now()
        
        # Set receipt email from patient's email if not provided
        if not self.receipt_email and self.patient.email:
            self.receipt_email = self.patient.email
        
        super().save(*args, **kwargs)


class Transaction(models.Model):
    """
    Model representing individual transaction records.
    
    This model tracks all financial transactions including
    payments, refunds, and transfers.
    """
    
    TRANSACTION_TYPES = [
        ('payment', 'Payment'),
        ('refund', 'Refund'),
        ('partial_refund', 'Partial Refund'),
        ('transfer', 'Transfer'),
        ('fee', 'Processing Fee'),
        ('chargeback', 'Chargeback'),
    ]
    
    # Identifiers
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    transaction_id = models.CharField(
        max_length=100,
        unique=True,
        help_text="Unique transaction identifier"
    )
    
    # Related payment
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='transactions',
        help_text="Associated payment record"
    )
    
    # Transaction details
    transaction_type = models.CharField(
        max_length=20,
        choices=TRANSACTION_TYPES,
        help_text="Type of transaction"
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Transaction amount"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Transaction currency"
    )
    
    # External references
    external_reference = models.CharField(
        max_length=255,
        blank=True,
        help_text="External system reference (Stripe, PayPal, etc.)"
    )
    
    # Additional information
    description = models.TextField(
        blank=True,
        help_text="Transaction description"
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional transaction metadata"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(
        default=timezone.now,
        help_text="When the transaction was processed"
    )
    
    class Meta:
        ordering = ['-processed_at']
        verbose_name = 'Transaction'
        verbose_name_plural = 'Transactions'
        indexes = [
            models.Index(fields=['payment', 'transaction_type']),
            models.Index(fields=['transaction_type', 'processed_at']),
            models.Index(fields=['external_reference']),
        ]
    
    def __str__(self):
        return f"Transaction {self.transaction_id} - {self.get_transaction_type_display()}"
    
    def save(self, *args, **kwargs):
        """Override save to generate transaction ID."""
        if not self.transaction_id:
            # Generate unique transaction ID
            self.transaction_id = f"TXN-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        super().save(*args, **kwargs)


class Invoice(models.Model):
    """
    Model representing payment invoices.
    
    This model generates and tracks invoices for appointments
    and medical services.
    """
    
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('sent', 'Sent'),
        ('paid', 'Paid'),
        ('overdue', 'Overdue'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
    ]
    
    # Identifiers
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    invoice_number = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique invoice number"
    )
    
    # Related objects
    appointment = models.OneToOneField(
        'doctors.Appointment',
        on_delete=models.CASCADE,
        related_name='invoice',
        help_text="Associated appointment"
    )
    payment = models.OneToOneField(
        Payment,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='invoice',
        help_text="Associated payment record"
    )
    
    # Invoice details
    patient_name = models.CharField(
        max_length=200,
        help_text="Patient's full name"
    )
    patient_email = models.EmailField(
        help_text="Patient's email address"
    )
    doctor_name = models.CharField(
        max_length=200,
        help_text="Doctor's full name"
    )
    
    # Financial details
    subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Subtotal amount"
    )
    tax_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Tax amount"
    )
    discount_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text="Discount amount"
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(Decimal('0.01'))],
        help_text="Total invoice amount"
    )
    currency = models.CharField(
        max_length=3,
        default='USD',
        help_text="Invoice currency"
    )
    
    # Status and dates
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='draft',
        db_index=True
    )
    issue_date = models.DateField(
        default=timezone.now,
        help_text="Invoice issue date"
    )
    due_date = models.DateField(
        help_text="Payment due date"
    )
    paid_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when invoice was paid"
    )
    
    # Additional information
    notes = models.TextField(
        blank=True,
        help_text="Additional invoice notes"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-issue_date', '-created_at']
        verbose_name = 'Invoice'
        verbose_name_plural = 'Invoices'
        indexes = [
            models.Index(fields=['status', 'due_date']),
            models.Index(fields=['patient_email', 'status']),
            models.Index(fields=['issue_date']),
        ]
    
    def __str__(self):
        return f"Invoice {self.invoice_number} - {self.total_amount} {self.currency}"
    
    @property
    def is_overdue(self):
        """Check if invoice is overdue."""
        return self.due_date < timezone.now().date() and self.status not in ['paid', 'cancelled', 'refunded']
    
    @property
    def days_until_due(self):
        """Calculate days until due date."""
        return (self.due_date - timezone.now().date()).days
    
    def get_absolute_url(self):
        """Return the absolute URL for this invoice."""
        return reverse('payments:invoice_detail', kwargs={'pk': self.pk})
    
    def save(self, *args, **kwargs):
        """Override save to generate invoice number and calculate totals."""
        if not self.invoice_number:
            # Generate unique invoice number
            self.invoice_number = f"INV-{timezone.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
        
        # Calculate total amount
        self.total_amount = self.subtotal + self.tax_amount - self.discount_amount
        
        # Set due date if not provided (default: 7 days from issue date)
        if not self.due_date:
            self.due_date = self.issue_date + timezone.timedelta(days=7)
        
        # Set paid date when status changes to paid
        if self.status == 'paid' and not self.paid_date:
            self.paid_date = timezone.now().date()
        
        # Update status to overdue if past due date
        if self.is_overdue and self.status not in ['paid', 'cancelled', 'refunded']:
            self.status = 'overdue'
        
        super().save(*args, **kwargs)


class PaymentMethod(models.Model):
    """
    Model representing saved payment methods for users.
    
    This model stores user's payment methods for quick checkout
    and recurring payments.
    """
    
    PAYMENT_METHOD_TYPES = [
        ('card', 'Credit/Debit Card'),
        ('bank_account', 'Bank Account'),
        ('digital_wallet', 'Digital Wallet'),
        ('other', 'Other'),
    ]
    
    # User and identification
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='payment_methods',
        help_text="User who owns this payment method"
    )
    
    # Stripe integration
    stripe_payment_method_id = models.CharField(
        max_length=255,
        unique=True,
        help_text="Stripe Payment Method ID"
    )
    
    # Payment method details
    payment_method_type = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_TYPES,
        help_text="Type of payment method"
    )
    brand = models.CharField(
        max_length=50,
        blank=True,
        help_text="Card brand (visa, mastercard, etc.)"
    )
    last_four = models.CharField(
        max_length=4,
        blank=True,
        help_text="Last four digits of card"
    )
    exp_month = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Card expiration month"
    )
    exp_year = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Card expiration year"
    )
    
    # Settings
    is_default = models.BooleanField(
        default=False,
        help_text="Whether this is the default payment method"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this payment method is active"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-is_default', '-created_at']
        verbose_name = 'Payment Method'
        verbose_name_plural = 'Payment Methods'
        indexes = [
            models.Index(fields=['user', 'is_active']),
            models.Index(fields=['user', 'is_default']),
        ]
    
    def __str__(self):
        if self.brand and self.last_four:
            return f"{self.brand.title()} ending in {self.last_four}"
        return f"{self.get_payment_method_type_display()}"
    
    def save(self, *args, **kwargs):
        """Override save to handle default payment method logic."""
        if self.is_default:
            # Ensure only one default payment method per user
            PaymentMethod.objects.filter(
                user=self.user,
                is_default=True
            ).exclude(pk=self.pk).update(is_default=False)
        
        super().save(*args, **kwargs)
