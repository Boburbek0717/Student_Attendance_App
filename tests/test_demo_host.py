import asyncio
import re
import unittest
from fastapi.testclient import TestClient
from scripts.demo_host import DemoLimits, settings
from scripts.portfolio_demo import portfolio_demo, DEMO_PASSWORD


class HostedDemoTests(unittest.TestCase):
    def test_host_settings_fail_closed(self):
        for env in ({}, {'RENDER':'true','SAT_FACTORY_PUBLIC_DEMO':'1','RENDER_EXTERNAL_HOSTNAME':'evil.test'},
                    {'RENDER':'true','SAT_FACTORY_PUBLIC_DEMO':'1','RENDER_EXTERNAL_HOSTNAME':'ok.onrender.com','PORT':'80'}):
            with self.assertRaises(ValueError): settings(env)
        self.assertEqual(settings({'RENDER':'true','SAT_FACTORY_PUBLIC_DEMO':'1',
            'RENDER_EXTERNAL_HOSTNAME':'sat-demo.onrender.com'}), ('sat-demo.onrender.com',10000))

    def test_public_https_access_and_protected_content(self):
        with portfolio_demo(public=True, allowed_hosts=['demo.onrender.com']) as app:
            with TestClient(app, base_url='https://demo.onrender.com') as client:
                page = client.get('/login')
                self.assertIn('secure', page.headers['set-cookie'].lower())
                self.assertIn('Public demo:', page.text)
                self.assertEqual(client.get('/healthz').text,'ok')
                self.assertEqual(client.get('/healthz',headers={'host':'evil.test'}).status_code,400)
                self.assertEqual(client.get('http://demo.onrender.com/login',follow_redirects=False).status_code,307)
                self.assertEqual(client.get('/docs').status_code,404)
                self.assertEqual(client.post('/teacher/questions/import', content=b'x'*(11*1024*1024)).status_code,403)
                self.assertIn('Disallow: /', client.get('/robots.txt').text)
                csrf = re.search(r'name="csrf" value="([^"]+)"', page.text)[1]
                response=client.post('/login',data=dict(csrf=csrf,username='demo-student',password=DEMO_PASSWORD))
                self.assertEqual(response.status_code,200)
                self.assertEqual(client.get('/teacher').status_code,403)
                for path in ['/teacher/students', '/teacher/groups', '/teacher/questions/import',
                             '/teacher/questions/new', '/teacher/questions/1/publication',
                             '/teacher/assignments/new']:
                    denied=client.post(path,data={'csrf':csrf})
                    self.assertEqual(denied.status_code,403)
                    self.assertIn('strict-transport-security',denied.headers)
                self.assertEqual(client.post('/student/goal',data=dict(csrf='bad',target_score='1400',version='0')).status_code,403)

    def test_limits_expire_and_lifetime_requires_restart_without_reading_upload(self):
        async def exercise():
            now=[0]
            async def downstream(scope, receive, send):
                await send({'type':'http.response.start','status':200,'headers':[]})
                await send({'type':'http.response.body','body':b'ok'})
            guard=DemoLimits(downstream,clock=lambda:now[0],request_limit=10,write_limit=2,lifetime_limit=3)
            async def request(path, method='POST'):
                messages=[]
                async def receive(): raise AssertionError('blocked body must not be read')
                async def send(message): messages.append(message)
                await guard({'type':'http','method':method,'path':path},receive,send)
                return messages[0]['status']
            self.assertEqual(await request('/teacher/questions/import'),403)
            self.assertEqual(await request('/login'),200)
            self.assertEqual(await request('/login'),200)
            self.assertEqual(await request('/login'),429)
            now[0]=61
            self.assertEqual(await request('/login'),200)
            self.assertEqual(await request('/login'),503)
            self.assertEqual(await request('/healthz','GET'),200)
            self.assertEqual(await request('/student','GET'),200)
            self.assertEqual(await request('/student/goal','PUT'),403)
        asyncio.run(exercise())
