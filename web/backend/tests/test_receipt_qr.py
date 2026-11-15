import json
from fastapi.testclient import TestClient
from test_auth import auth_app, login
from test_operations import setup_catalog, draft, confirm, receipt_body, post

def test_delivery_qr_previews_then_posts_once_without_stock_side_effect(auth_app):
    app,_=auth_app
    with TestClient(app) as client:
        client.headers.update(login(client));warehouse,_,supplier=setup_catalog(client)
        item=post(client,'/products',{'name':'Physical','sku':'PHYSICAL','product_type':'physical_SIM','carrier':'DemoCarrier','destination_country':'DemoLand'}).json()['id']
        order=confirm(client,draft(client,warehouse,item,supplier))
        body=receipt_body(order,4,'QR-DELIVERY')
        endpoint=f'/api/v1/operations/orders/{order["id"]}/receipt-qr'
        generated=client.post(endpoint,json=body)
        assert generated.status_code==200,generated.text
        qr=generated.json();assert qr['image'].startswith('data:image/svg+xml')
        assert json.loads(qr['payload'])['format']=='sigma-delivery-v1'
        preview=client.post(endpoint+'/preview',json={'payload':qr['payload']})
        assert preview.status_code==200 and preview.json()['posted'] is False
        assert client.get('/api/v1/operations/stock').json()['total']==0
        assert post(client,f'/orders/{order["id"]}/receipts',body).status_code==201
        assert client.get('/api/v1/operations/stock').json()['items'][0]['on_hand_qty']==4
        assert client.post(endpoint+'/preview',json={'payload':qr['payload']}).status_code==409
        assert post(client,f'/orders/{order["id"]}/receipts',body).status_code==409

def test_qr_rejects_wrong_order_extra_keys_activation_payload_and_esim(auth_app):
    app,_=auth_app
    with TestClient(app) as client:
        client.headers.update(login(client));warehouse,item,supplier=setup_catalog(client)
        order=confirm(client,draft(client,warehouse,item,supplier))
        endpoint=f'/api/v1/operations/orders/{order["id"]}/receipt-qr'
        assert client.post(endpoint,json=receipt_body(order,4)).status_code==422
        valid={'format':'sigma-delivery-v1','order_id':order['id'],'external_ref':'QR','lines':[{'order_line_id':order['lines'][0]['id'],'quantity':1}]}
        for payload in ['LPA:1$not-an-inventory-qr','https://example.invalid/qr',json.dumps({**valid,'order_id':999}),json.dumps({**valid,'token':'unexpected'}),'{"format":"x","format":"y"}']:
            assert client.post(endpoint+'/preview',json={'payload':payload}).status_code==422
        assert client.post(endpoint+'/preview',json={'payload':json.dumps(valid)}).status_code==422
    with TestClient(app) as supplier_client:
        login(supplier_client,'partner-a')
        assert supplier_client.post(endpoint+'/preview',json={'payload':'x'}).status_code==403
