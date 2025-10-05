from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    # Payment management
    path('', views.PaymentListView.as_view(), name='list'),
    path('<uuid:pk>/', views.PaymentDetailView.as_view(), name='detail'),
    path('create/<int:appointment_id>/', views.CreatePaymentView.as_view(), name='create'),
    
    # Payment processing
    path('success/', views.PaymentSuccessView.as_view(), name='success'),
    path('cancel/', views.PaymentCancelView.as_view(), name='cancel'),
    path('webhook/', views.PaymentWebhookView.as_view(), name='webhook'),
    
    # Refunds
    path('<uuid:payment_id>/refund/', views.process_refund, name='refund'),
    
    # Payment methods
    path('payment-methods/', views.PaymentMethodListView.as_view(), name='payment_methods'),
    path('payment-methods/create/', views.payment_method_create, name='payment_method_create'),
    path('payment-methods/<uuid:method_id>/set-default/', views.set_default_payment_method, name='set_default_payment_method'),
    
    # Invoices
    path('invoices/', views.InvoiceListView.as_view(), name='invoice_list'),
    path('invoices/<uuid:pk>/', views.InvoiceDetailView.as_view(), name='invoice_detail'),
    
    # Doctor dashboard
    path('doctor/dashboard/', views.DoctorPaymentDashboardView.as_view(), name='doctor_dashboard'),
]
