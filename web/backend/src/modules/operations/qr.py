"""Versioned delivery-note QR. It identifies a lot, never an activation credential."""
import json
from sqlalchemy import select
from pydantic import ValidationError
from core.errors import DomainError
from modules.operations.schemas import OpsReceiptInput
from modules.operations.models import StockDocument
from modules.operations.service import order_view

FORMAT = 'sigma-delivery-v1'


def validate_delivery(session, order_id, payload):
    order = order_view(session, order_id)
    if order['status'] not in {'ordered','partially_received'}:
        raise DomainError('order_not_receivable','Đơn chưa xác nhận hoặc đã kết thúc.',409)
    if payload.expected_version != order['version']:
        raise DomainError('version_conflict','Đơn đã thay đổi. Đóng form và mở lại để đối chiếu.',409)
    known = {line['id']:line for line in order['lines']}
    for entry in payload.lines:
        line = known.get(entry.order_line_id)
        if line is None or line['product_type'] != 'physical_SIM':
            raise DomainError('invalid_delivery_qr','QR này chỉ dùng cho dòng SIM vật lý thuộc đơn đang mở.')
        if entry.quantity > line['remaining_qty']:
            raise DomainError('over_receipt','Số lượng trên QR vượt phần chưa nhận.',409)
    if session.scalar(select(StockDocument.id).where(StockDocument.order_id==order_id,StockDocument.external_ref==payload.external_ref)):
        raise DomainError('delivery_already_received','Phiếu giao này đã được ghi nhận; không nhận lại.',409)
    return order


def create_qr(session, order_id, payload):
    validate_delivery(session,order_id,payload)
    body = dict(format=FORMAT,order_id=order_id,external_ref=payload.external_ref,
                lines=[line.model_dump() for line in payload.lines])
    text = json.dumps(body,ensure_ascii=True,separators=(',',':'))
    if len(text)>1800:
        raise DomainError('qr_too_large','Phiếu có quá nhiều dòng cho một QR. Tách thành phiếu giao nhỏ hơn.')
    import segno
    return dict(payload=text,image=segno.make_qr(text,error='m').svg_data_uri(scale=4),format=FORMAT)


def preview_qr(session,order_id,text):
    def unique_keys(pairs):
        value={}
        for key,item in pairs:
            if key in value:
                raise ValueError('Duplicate field')
            value[key]=item
        return value
    try:
        body=json.loads(text,object_pairs_hook=unique_keys)
        if not isinstance(body,dict) or set(body)!={'format','order_id','external_ref','lines'} or body['format']!=FORMAT:
            raise ValueError('Invalid format')
        if type(body['order_id']) is not int or body['order_id']!=order_id:
            raise ValueError('Different order')
        order=order_view(session,order_id)
        from modules.operations.service import today
        receipt=OpsReceiptInput(expected_version=order['version'],occurred_on=today(),external_ref=body['external_ref'],lines=body['lines'])
        validate_delivery(session,order_id,receipt)
        return dict(order_id=order_id,version=order['version'],external_ref=receipt.external_ref,
            lines=[line.model_dump() for line in receipt.lines],posted=False)
    except (ValueError, TypeError, KeyError, ValidationError, RecursionError):
        raise DomainError('invalid_delivery_qr','Mã không đúng định dạng phiếu giao SIGMA hoặc thuộc đơn khác. Không dùng QR kích hoạt eSIM.') from None
