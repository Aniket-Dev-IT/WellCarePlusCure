import stripe
import logging
from decimal import Decimal
from typing import Dict, Optional, Any
from django.conf import settings
from django.contrib.auth.models import User
from django.utils import timezone

from .models import Payment, Transaction, PaymentMethod
from apps.doctors.models import Doctor, Appointment

logger = logging.getLogger(__name__)

# Initialize Stripe with secret key
stripe.api_key = settings.STRIPE_SECRET_KEY


class StripePaymentService:
    """
    Service class for handling Stripe payment operations.
    
    This service provides methods to create payment intents,
    process payments, handle refunds, and manage payment methods.
    """
    
    @staticmethod
    def create_payment_intent(
        amount: Decimal,
        currency: str = 'USD',
        customer_email: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create a Stripe Payment Intent for processing payment.
        
        Args:
            amount: Payment amount in the smallest currency unit (e.g., cents)
            currency: Payment currency (default: USD)
            customer_email: Customer's email address
            metadata: Additional metadata for the payment
            
        Returns:
            Dictionary containing payment intent details
        """
        try:
            # Convert amount to cents (Stripe requires smallest currency unit)
            amount_cents = int(amount * 100)
            
            intent_data = {
                'amount': amount_cents,
                'currency': currency.lower(),
                'automatic_payment_methods': {
                    'enabled': True,
                },
                'metadata': metadata or {},
            }
            
            if customer_email:
                intent_data['receipt_email'] = customer_email
            
            # Create the payment intent
            intent = stripe.PaymentIntent.create(**intent_data)
            
            logger.info(f"Payment intent created: {intent.id}")
            
            return {
                'success': True,
                'payment_intent': intent,
                'client_secret': intent.client_secret,
                'payment_intent_id': intent.id,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating payment intent: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
            }
        except Exception as e:
            logger.error(f"Unexpected error creating payment intent: {e}")
            return {
                'success': False,
                'error': 'An unexpected error occurred',
                'error_type': 'UnknownError',
            }
    
    @staticmethod
    def confirm_payment_intent(payment_intent_id: str) -> Dict[str, Any]:
        """
        Confirm a payment intent and retrieve its status.
        
        Args:
            payment_intent_id: Stripe Payment Intent ID
            
        Returns:
            Dictionary containing confirmation result
        """
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            
            logger.info(f"Payment intent retrieved: {intent.id}, status: {intent.status}")
            
            return {
                'success': True,
                'payment_intent': intent,
                'status': intent.status,
                'amount_received': Decimal(str(intent.amount_received)) / 100,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error confirming payment intent: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
            }
    
    @staticmethod
    def create_refund(
        payment_intent_id: str,
        amount: Optional[Decimal] = None,
        reason: str = 'requested_by_customer'
    ) -> Dict[str, Any]:
        """
        Create a refund for a payment.
        
        Args:
            payment_intent_id: Stripe Payment Intent ID
            amount: Refund amount (if None, full refund)
            reason: Reason for refund
            
        Returns:
            Dictionary containing refund result
        """
        try:
            refund_data = {
                'payment_intent': payment_intent_id,
                'reason': reason,
            }
            
            if amount is not None:
                refund_data['amount'] = int(amount * 100)
            
            refund = stripe.Refund.create(**refund_data)
            
            logger.info(f"Refund created: {refund.id} for payment {payment_intent_id}")
            
            return {
                'success': True,
                'refund': refund,
                'refund_id': refund.id,
                'amount': Decimal(str(refund.amount)) / 100,
                'status': refund.status,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating refund: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
            }
    
    @staticmethod
    def create_customer(user: User) -> Dict[str, Any]:
        """
        Create a Stripe customer for a user.
        
        Args:
            user: Django User instance
            
        Returns:
            Dictionary containing customer creation result
        """
        try:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.get_full_name() or user.username,
                metadata={
                    'user_id': str(user.id),
                    'username': user.username,
                }
            )
            
            logger.info(f"Stripe customer created: {customer.id} for user {user.id}")
            
            return {
                'success': True,
                'customer': customer,
                'customer_id': customer.id,
            }
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error creating customer: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': type(e).__name__,
            }


class PaymentService:
    """
    Service class for managing payment operations.
    
    This service handles payment creation, status updates,
    and integration with the appointment system.
    """
    
    @staticmethod
    def create_appointment_payment(
        appointment: Appointment,
        payment_type: str = 'consultation'
    ) -> Payment:
        """
        Create a payment record for an appointment.
        
        Args:
            appointment: Appointment instance
            payment_type: Type of payment
            
        Returns:
            Created Payment instance
        """
        payment = Payment.objects.create(
            appointment=appointment,
            patient=appointment.patient,
            doctor=appointment.doctor,
            payment_type=payment_type,
            amount=appointment.doctor.consultation_fee,
            description=f"Consultation with {appointment.doctor.display_name}",
        )
        
        logger.info(f"Payment created: {payment.payment_reference} for appointment {appointment.id}")
        
        return payment
    
    @staticmethod
    def process_payment_intent(
        payment: Payment,
        payment_intent_result: Dict[str, Any]
    ) -> bool:
        """
        Process payment intent result and update payment record.
        
        Args:
            payment: Payment instance
            payment_intent_result: Result from Stripe payment intent
            
        Returns:
            Boolean indicating success
        """
        try:
            if payment_intent_result.get('success'):
                intent = payment_intent_result['payment_intent']
                
                # Update payment with Stripe details
                payment.stripe_payment_intent_id = intent.id
                payment.status = 'processing'
                
                if intent.status == 'succeeded':
                    payment.status = 'succeeded'
                    payment.paid_at = timezone.now()
                    
                    # Update appointment payment status
                    payment.appointment.is_paid = True
                    payment.appointment.save(update_fields=['is_paid'])
                    
                elif intent.status == 'requires_payment_method':
                    payment.status = 'pending'
                elif intent.status in ['processing', 'requires_confirmation']:
                    payment.status = 'processing'
                else:
                    payment.status = 'failed'
                
                payment.save()
                
                # Create transaction record
                Transaction.objects.create(
                    payment=payment,
                    transaction_type='payment',
                    amount=payment.amount,
                    currency=payment.currency,
                    external_reference=intent.id,
                    description=f"Payment for {payment.payment_reference}",
                    metadata={
                        'stripe_status': intent.status,
                        'payment_method': getattr(intent, 'payment_method', None),
                    }
                )
                
                return True
            else:
                payment.status = 'failed'
                payment.save()
                return False
                
        except Exception as e:
            logger.error(f"Error processing payment intent for payment {payment.id}: {e}")
            payment.status = 'failed'
            payment.save()
            return False
    
    @staticmethod
    def process_refund(payment: Payment, refund_amount: Optional[Decimal] = None, reason: str = '') -> bool:
        """
        Process a refund for a payment.
        
        Args:
            payment: Payment instance
            refund_amount: Amount to refund (if None, full refund)
            reason: Reason for refund
            
        Returns:
            Boolean indicating success
        """
        try:
            if not payment.stripe_payment_intent_id:
                logger.error(f"Cannot refund payment {payment.id}: No Stripe payment intent ID")
                return False
            
            # Create refund via Stripe
            refund_result = StripePaymentService.create_refund(
                payment.stripe_payment_intent_id,
                refund_amount,
                reason or 'requested_by_customer'
            )
            
            if refund_result.get('success'):
                refund_amt = refund_amount or payment.amount
                payment.refund_amount += refund_amt
                payment.refund_reason = reason
                
                if payment.refund_amount >= payment.amount:
                    payment.status = 'refunded'
                else:
                    payment.status = 'partially_refunded'
                
                payment.save()
                
                # Create refund transaction record
                Transaction.objects.create(
                    payment=payment,
                    transaction_type='refund',
                    amount=-refund_amt,  # Negative amount for refunds
                    currency=payment.currency,
                    external_reference=refund_result['refund_id'],
                    description=f"Refund for {payment.payment_reference}",
                    metadata={
                        'refund_reason': reason,
                        'stripe_refund_status': refund_result.get('status'),
                    }
                )
                
                return True
            else:
                logger.error(f"Failed to create Stripe refund for payment {payment.id}: {refund_result.get('error')}")
                return False
                
        except Exception as e:
            logger.error(f"Error processing refund for payment {payment.id}: {e}")
            return False


class PaymentMethodService:
    """
    Service class for managing user payment methods.
    
    This service handles saving and retrieving payment methods
    for users to enable quick checkout.
    """
    
    @staticmethod
    def save_payment_method(
        user: User,
        stripe_payment_method_id: str,
        is_default: bool = False
    ) -> Optional[PaymentMethod]:
        """
        Save a payment method for a user.
        
        Args:
            user: User instance
            stripe_payment_method_id: Stripe Payment Method ID
            is_default: Whether this should be the default payment method
            
        Returns:
            Created PaymentMethod instance or None if failed
        """
        try:
            # Retrieve payment method details from Stripe
            pm = stripe.PaymentMethod.retrieve(stripe_payment_method_id)
            
            # Extract payment method details
            payment_method_data = {
                'user': user,
                'stripe_payment_method_id': stripe_payment_method_id,
                'is_default': is_default,
            }
            
            if pm.type == 'card' and pm.card:
                payment_method_data.update({
                    'payment_method_type': 'card',
                    'brand': pm.card.brand,
                    'last_four': pm.card.last4,
                    'exp_month': pm.card.exp_month,
                    'exp_year': pm.card.exp_year,
                })
            else:
                payment_method_data['payment_method_type'] = pm.type
            
            payment_method = PaymentMethod.objects.create(**payment_method_data)
            
            logger.info(f"Payment method saved: {payment_method.id} for user {user.id}")
            
            return payment_method
            
        except stripe.error.StripeError as e:
            logger.error(f"Stripe error saving payment method: {e}")
            return None
        except Exception as e:
            logger.error(f"Error saving payment method: {e}")
            return None
    
    @staticmethod
    def get_user_payment_methods(user: User):
        """
        Get all active payment methods for a user.
        
        Args:
            user: User instance
            
        Returns:
            QuerySet of PaymentMethod instances
        """
        return PaymentMethod.objects.filter(
            user=user,
            is_active=True
        ).order_by('-is_default', '-created_at')
    
    @staticmethod
    def set_default_payment_method(user: User, payment_method_id: str) -> bool:
        """
        Set a payment method as the default for a user.
        
        Args:
            user: User instance
            payment_method_id: PaymentMethod ID to set as default
            
        Returns:
            Boolean indicating success
        """
        try:
            payment_method = PaymentMethod.objects.get(
                id=payment_method_id,
                user=user,
                is_active=True
            )
            
            # Remove default from other payment methods
            PaymentMethod.objects.filter(
                user=user,
                is_default=True
            ).update(is_default=False)
            
            # Set as default
            payment_method.is_default = True
            payment_method.save()
            
            return True
            
        except PaymentMethod.DoesNotExist:
            logger.error(f"Payment method {payment_method_id} not found for user {user.id}")
            return False
        except Exception as e:
            logger.error(f"Error setting default payment method: {e}")
            return False
