import base64
import hashlib
import hmac
import json
import logging
import uuid
from datetime import timezone as dt_timezone

from django.conf import settings
from django.utils.dateparse import parse_datetime
from django.utils import timezone


logger = logging.getLogger(__name__)


class CashfreeGatewayError(Exception):
    """Raised when Cashfree order creation or fetch fails."""


class CashfreeWebhookError(Exception):
    """Raised when the webhook payload or signature is invalid."""


def _get_cashfree_sdk():
    try:
        from cashfree_pg.api_client import Cashfree
        from cashfree_pg.models.create_order_request import CreateOrderRequest
        from cashfree_pg.models.customer_details import CustomerDetails
        from cashfree_pg.models.order_meta import OrderMeta
    except ImportError as exc:
        raise CashfreeGatewayError('cashfree-pg is not installed. Run pip install cashfree-pg.') from exc
    return Cashfree, CreateOrderRequest, CustomerDetails, OrderMeta


def _cashfree_environment_name():
    return (
        getattr(settings, 'CASHFREE_ENV', None)
        or getattr(settings, 'CASHFREE_ENVIRONMENT', 'SANDBOX')
        or 'SANDBOX'
    ).upper()


def _cashfree_error_message(exc):
    parts = []
    status = getattr(exc, 'status', None)
    reason = getattr(exc, 'reason', None)
    body = getattr(exc, 'body', None)

    if status:
        parts.append(f'status={status}')
    if reason:
        parts.append(str(reason))
    if body:
        parts.append(str(body))

    return ' | '.join(parts) or str(exc)


def _get_payment_link(data):
    payment_link = getattr(data, 'payment_link', '') or ''
    payments = getattr(data, 'payments', None)

    if payment_link or not payments:
        return payment_link

    return (
        getattr(payments, 'url', '')
        or getattr(payments, 'payment_link', '')
        or getattr(payments, 'web', '')
        or ''
    )


def _configure_cashfree_client():
    app_id = (settings.CASHFREE_APP_ID or '').strip()
    secret_key = (settings.CASHFREE_SECRET_KEY or '').strip()

    if not app_id or not secret_key or app_id == 'YOUR_APP_ID' or secret_key == 'YOUR_SECRET_KEY':
        logger.error('Cashfree credentials are missing or still set to placeholder values.')
        raise CashfreeGatewayError(
            'Cashfree credentials missing. Set CASHFREE_APP_ID and CASHFREE_SECRET_KEY.'
        )

    Cashfree, CreateOrderRequest, CustomerDetails, OrderMeta = _get_cashfree_sdk()
    environment = Cashfree.PRODUCTION if _cashfree_environment_name() == 'PRODUCTION' else Cashfree.SANDBOX
    client = Cashfree(
        environment,
        XClientId=app_id,
        XClientSecret=secret_key,
    )
    return client, CreateOrderRequest, CustomerDetails, OrderMeta


def build_cashfree_order_id(order):
    if order.cashfree_order_id and not str(order.cashfree_order_id).startswith('TMP-'):
        return order.cashfree_order_id
    return f'ORD-{order.pk:06d}'


def normalize_cashfree_phone(phone_number):
    digits = ''.join(ch for ch in (phone_number or '') if ch.isdigit())
    if len(digits) >= 10:
        digits = digits[-10:]

    if len(digits) != 10:
        fallback = ''.join(ch for ch in settings.CASHFREE_CUSTOMER_PHONE_FALLBACK if ch.isdigit())
        digits = fallback[-10:]

    if len(digits) != 10:
        raise CashfreeGatewayError('Cashfree requires a valid 10-digit customer phone number.')

    return digits


def create_cashfree_order(order, return_url, notify_url):
    client, CreateOrderRequest, CustomerDetails, OrderMeta = _configure_cashfree_client()
    cashfree_order_id = build_cashfree_order_id(order)

    customer_details = CustomerDetails(
        customer_id=f'CUST-{order.pk:06d}',
        customer_name=order.full_name,
        customer_email=order.email,
        customer_phone=normalize_cashfree_phone(order.phone_number),
    )
    order_meta = OrderMeta(return_url=return_url, notify_url=notify_url)
    create_order_request = CreateOrderRequest(
        order_id=cashfree_order_id,
        order_amount=float(order.total_price),
        order_currency=settings.CASHFREE_CURRENCY,
        customer_details=customer_details,
        order_meta=order_meta,
        order_note=f'Glowall order #{order.pk}',
    )
    idempotency_key = str(uuid.uuid5(uuid.NAMESPACE_URL, f'glowall-checkout-{order.pk}'))

    try:
        response = client.PGCreateOrder(
            settings.CASHFREE_API_VERSION,
            create_order_request,
            x_request_id=f'checkout-{order.pk}',
            x_idempotency_key=idempotency_key,
        )
    except Exception as exc:
        logger.exception('Cashfree create order failed for order %s', order.pk)
        raise CashfreeGatewayError(_cashfree_error_message(exc)) from exc

    data = getattr(response, 'data', None)
    if not data:
        logger.error('Cashfree create order returned an empty response for order %s', order.pk)
        raise CashfreeGatewayError('Invalid response from Cashfree.')

    payment_session_id = getattr(data, 'payment_session_id', '')
    payment_link = _get_payment_link(data)
    if not payment_link and not payment_session_id:
        logger.error('Cashfree response missing both payment link and payment session id for order %s', order.pk)
        raise CashfreeGatewayError('Invalid response from Cashfree.')

    return {
        'cashfree_order_id': getattr(data, 'order_id', cashfree_order_id) or cashfree_order_id,
        'cashfree_cf_order_id': getattr(data, 'cf_order_id', ''),
        'payment_session_id': payment_session_id,
        'payment_link': payment_link,
        'order_status': getattr(data, 'order_status', ''),
    }


def fetch_cashfree_order(order):
    if not order.cashfree_order_id:
        raise CashfreeGatewayError('Cashfree order id is missing for this order.')

    client, _, _, _ = _configure_cashfree_client()

    try:
        order_response = client.PGFetchOrder(
            settings.CASHFREE_API_VERSION,
            order.cashfree_order_id,
            x_request_id=f'fetch-order-{order.pk}',
        )
        payments_response = client.PGOrderFetchPayments(
            settings.CASHFREE_API_VERSION,
            order.cashfree_order_id,
            x_request_id=f'fetch-payments-{order.pk}',
        )
    except Exception as exc:
        logger.exception('Cashfree fetch order failed for order %s', order.pk)
        raise CashfreeGatewayError(_cashfree_error_message(exc)) from exc

    order_data = getattr(order_response, 'data', None)
    if not order_data:
        logger.error('Cashfree order fetch returned an empty response for order %s', order.pk)
        raise CashfreeGatewayError('Cashfree returned an empty order response.')

    payments = []
    for payment in getattr(payments_response, 'data', None) or []:
        payments.append(
            {
                'cf_payment_id': getattr(payment, 'cf_payment_id', ''),
                'payment_status': getattr(payment, 'payment_status', ''),
                'payment_message': getattr(payment, 'payment_message', ''),
                'payment_time': getattr(payment, 'payment_time', ''),
                'payment_completion_time': getattr(payment, 'payment_completion_time', ''),
            }
        )

    return {
        'order_status': getattr(order_data, 'order_status', ''),
        'payment_session_id': getattr(order_data, 'payment_session_id', ''),
        'payments': payments,
    }


def map_payment_status(order_status='', payment_status=''):
    normalized_payment_status = (payment_status or '').upper()
    normalized_order_status = (order_status or '').upper()

    if normalized_payment_status == 'SUCCESS' or normalized_order_status == 'PAID':
        return 'SUCCESS'
    if normalized_payment_status in {'FAILED', 'USER_DROPPED', 'CANCELLED'}:
        return 'FAILED'
    if normalized_order_status in {'EXPIRED', 'TERMINATED'}:
        return 'FAILED'
    return 'PENDING'


def parse_cashfree_timestamp(value):
    parsed = parse_datetime(value or '')
    if not parsed:
        return None
    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, dt_timezone.utc)
    return parsed


def verify_webhook_signature(raw_body, signature, timestamp):
    secret_key = (settings.CASHFREE_SECRET_KEY or '').strip()
    if not secret_key or secret_key == 'YOUR_SECRET_KEY':
        raise CashfreeWebhookError('Cashfree secret key is missing.')
    if not signature or not timestamp:
        raise CashfreeWebhookError('Cashfree webhook signature headers are missing.')

    signed_payload = f'{timestamp}{raw_body}'.encode('utf-8')
    expected_signature = base64.b64encode(
        hmac.new(secret_key.encode('utf-8'), signed_payload, hashlib.sha256).digest()
    ).decode('utf-8')

    if not hmac.compare_digest(expected_signature, signature):
        raise CashfreeWebhookError('Cashfree webhook signature verification failed.')


def parse_webhook_payload(raw_body):
    try:
        payload = json.loads(raw_body or '{}')
    except json.JSONDecodeError as exc:
        raise CashfreeWebhookError('Invalid Cashfree webhook payload.') from exc

    data = payload.get('data') or {}
    order_data = data.get('order') or {}
    payment_data = data.get('payment') or {}
    error_details = data.get('error_details') or {}

    cashfree_order_id = order_data.get('order_id') or payment_data.get('order_id')
    if not cashfree_order_id:
        raise CashfreeWebhookError('Cashfree webhook payload is missing the order id.')

    return {
        'cashfree_order_id': cashfree_order_id,
        'payment_status': payment_data.get('payment_status', ''),
        'cf_payment_id': payment_data.get('cf_payment_id', ''),
        'payment_message': payment_data.get('payment_message') or error_details.get('error_description', ''),
        'payment_time': payment_data.get('payment_completion_time') or payment_data.get('payment_time', ''),
    }
