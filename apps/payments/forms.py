from django import forms
from decimal import Decimal
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Fieldset, Submit, Row, Column, HTML, Div
from crispy_forms.bootstrap import FormActions

from .models import Payment, Invoice


class PaymentForm(forms.ModelForm):
    """
    Form for creating and updating payments.
    """
    
    class Meta:
        model = Payment
        fields = [
            'payment_type', 
            'amount', 
            'currency', 
            'description',
        ]
        widgets = {
            'amount': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0.01',
                'class': 'form-control',
                'placeholder': '0.00'
            }),
            'description': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Enter payment description...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'needs-validation'
        self.helper.attrs = {'novalidate': ''}
        
        self.helper.layout = Layout(
            Fieldset(
                'Payment Details',
                Row(
                    Column('payment_type', css_class='form-group col-md-6 mb-0'),
                    Column('currency', css_class='form-group col-md-6 mb-0'),
                ),
                'amount',
                'description',
            ),
            FormActions(
                Submit('submit', 'Create Payment', css_class='btn btn-primary'),
                HTML('<a href="{% url \'payments:list\' %}" class="btn btn-secondary">Cancel</a>')
            )
        )


class PaymentIntentForm(forms.Form):
    """
    Form for creating a Stripe payment intent.
    """
    
    amount = forms.DecimalField(
        min_value=Decimal('0.01'),
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'step': '0.01',
            'min': '0.01',
            'class': 'form-control',
            'placeholder': '0.00'
        }),
        help_text="Amount to charge (in your local currency)"
    )
    
    currency = forms.ChoiceField(
        choices=[
            ('USD', 'US Dollar'),
            ('EUR', 'Euro'),
            ('GBP', 'British Pound'),
            ('CAD', 'Canadian Dollar'),
            ('AUD', 'Australian Dollar'),
        ],
        initial='USD',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    save_payment_method = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Save this payment method for future use"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_id = 'payment-form'
        self.helper.form_class = 'needs-validation'
        
        self.helper.layout = Layout(
            HTML('<div id="payment-element"><!-- Stripe Elements will create form elements here --></div>'),
            Row(
                Column('amount', css_class='form-group col-md-6 mb-0'),
                Column('currency', css_class='form-group col-md-6 mb-0'),
            ),
            Div(
                HTML('''
                <div class="form-check">
                    <input type="checkbox" class="form-check-input" id="save-payment-method" name="save_payment_method">
                    <label class="form-check-label" for="save-payment-method">
                        Save this payment method for future use
                    </label>
                </div>
                '''),
                css_class='mb-3'
            ),
            HTML('<div id="payment-messages" class="alert" style="display: none;"></div>'),
            FormActions(
                HTML('<button type="submit" id="submit-payment" class="btn btn-primary">Pay Now</button>'),
                HTML('<div id="payment-spinner" class="spinner-border spinner-border-sm text-primary" role="status" style="display: none;"><span class="sr-only">Processing...</span></div>')
            )
        )


class RefundForm(forms.Form):
    """
    Form for processing refunds.
    """
    
    REFUND_REASONS = [
        ('requested_by_customer', 'Requested by Customer'),
        ('duplicate', 'Duplicate Payment'),
        ('fraudulent', 'Fraudulent Transaction'),
        ('appointment_cancelled', 'Appointment Cancelled'),
        ('service_not_provided', 'Service Not Provided'),
        ('other', 'Other'),
    ]
    
    refund_amount = forms.DecimalField(
        min_value=Decimal('0.01'),
        max_digits=10,
        decimal_places=2,
        required=False,
        widget=forms.NumberInput(attrs={
            'step': '0.01',
            'min': '0.01',
            'class': 'form-control',
            'placeholder': 'Leave blank for full refund'
        }),
        help_text="Amount to refund (leave blank for full refund)"
    )
    
    reason = forms.ChoiceField(
        choices=REFUND_REASONS,
        initial='requested_by_customer',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'class': 'form-control',
            'placeholder': 'Additional notes about the refund...'
        }),
        help_text="Optional notes about the refund"
    )
    
    def __init__(self, payment=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.payment = payment
        
        if payment:
            # Set max refund amount
            max_refundable = payment.amount - payment.refund_amount
            self.fields['refund_amount'].widget.attrs.update({
                'max': str(max_refundable),
                'placeholder': f'Max refundable: ${max_refundable}'
            })
        
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'needs-validation'
        
        self.helper.layout = Layout(
            Fieldset(
                'Refund Details',
                'refund_amount',
                'reason',
                'notes',
            ),
            FormActions(
                Submit('submit', 'Process Refund', css_class='btn btn-warning'),
                HTML('<button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>')
            )
        )
    
    def clean_refund_amount(self):
        refund_amount = self.cleaned_data.get('refund_amount')
        
        if self.payment and refund_amount:
            max_refundable = self.payment.amount - self.payment.refund_amount
            if refund_amount > max_refundable:
                raise forms.ValidationError(
                    f'Refund amount cannot exceed ${max_refundable} (remaining after previous refunds)'
                )
        
        return refund_amount


class InvoiceForm(forms.ModelForm):
    """
    Form for creating and updating invoices.
    """
    
    class Meta:
        model = Invoice
        fields = [
            'patient_name',
            'patient_email', 
            'doctor_name',
            'subtotal',
            'tax_amount',
            'discount_amount',
            'currency',
            'due_date',
            'notes',
        ]
        widgets = {
            'patient_name': forms.TextInput(attrs={'class': 'form-control'}),
            'patient_email': forms.EmailInput(attrs={'class': 'form-control'}),
            'doctor_name': forms.TextInput(attrs={'class': 'form-control'}),
            'subtotal': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0.01',
                'class': 'form-control'
            }),
            'tax_amount': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0.00',
                'class': 'form-control'
            }),
            'discount_amount': forms.NumberInput(attrs={
                'step': '0.01',
                'min': '0.00',
                'class': 'form-control'
            }),
            'due_date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Additional invoice notes...'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'needs-validation'
        
        self.helper.layout = Layout(
            Fieldset(
                'Invoice Information',
                Row(
                    Column('patient_name', css_class='form-group col-md-6 mb-0'),
                    Column('patient_email', css_class='form-group col-md-6 mb-0'),
                ),
                'doctor_name',
                Row(
                    Column('subtotal', css_class='form-group col-md-4 mb-0'),
                    Column('tax_amount', css_class='form-group col-md-4 mb-0'),
                    Column('discount_amount', css_class='form-group col-md-4 mb-0'),
                ),
                Row(
                    Column('currency', css_class='form-group col-md-6 mb-0'),
                    Column('due_date', css_class='form-group col-md-6 mb-0'),
                ),
                'notes',
            ),
            FormActions(
                Submit('submit', 'Save Invoice', css_class='btn btn-primary'),
                HTML('<a href="{% url \'payments:invoice_list\' %}" class="btn btn-secondary">Cancel</a>')
            )
        )


class PaymentMethodForm(forms.Form):
    """
    Form for managing payment methods.
    """
    
    set_default = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        help_text="Set this as your default payment method"
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'post'
        self.helper.form_class = 'payment-method-form'
        
        self.helper.layout = Layout(
            HTML('<div id="payment-method-element"><!-- Stripe Elements will create form elements here --></div>'),
            Div(
                HTML('''
                <div class="form-check">
                    <input type="checkbox" class="form-check-input" id="set-default" name="set_default">
                    <label class="form-check-label" for="set-default">
                        Set as default payment method
                    </label>
                </div>
                '''),
                css_class='mb-3'
            ),
            HTML('<div id="payment-method-messages" class="alert" style="display: none;"></div>'),
            FormActions(
                HTML('<button type="submit" id="save-payment-method" class="btn btn-primary">Save Payment Method</button>'),
                HTML('<div id="payment-method-spinner" class="spinner-border spinner-border-sm text-primary" role="status" style="display: none;"><span class="sr-only">Saving...</span></div>')
            )
        )


class PaymentSearchForm(forms.Form):
    """
    Form for searching and filtering payments.
    """
    
    STATUS_CHOICES = [
        ('', 'All Statuses'),
    ] + Payment.STATUS_CHOICES
    
    PAYMENT_TYPE_CHOICES = [
        ('', 'All Types'),
    ] + Payment.PAYMENT_TYPES
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by reference, patient, or doctor...'
        })
    )
    
    status = forms.ChoiceField(
        required=False,
        choices=STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    payment_type = forms.ChoiceField(
        required=False,
        choices=PAYMENT_TYPE_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = 'get'
        self.helper.form_class = 'payment-search-form'
        
        self.helper.layout = Layout(
            Row(
                Column('search', css_class='form-group col-md-4 mb-0'),
                Column('status', css_class='form-group col-md-2 mb-0'),
                Column('payment_type', css_class='form-group col-md-2 mb-0'),
                Column('date_from', css_class='form-group col-md-2 mb-0'),
                Column('date_to', css_class='form-group col-md-2 mb-0'),
            ),
            FormActions(
                Submit('submit', 'Search', css_class='btn btn-primary btn-sm'),
                HTML('<a href="?" class="btn btn-outline-secondary btn-sm">Clear</a>')
            )
        )
