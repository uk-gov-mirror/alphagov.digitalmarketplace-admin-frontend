try:
    from urlparse import urlsplit
    from StringIO import StringIO
except ImportError:
    from urllib.parse import urlsplit
    from io import BytesIO as StringIO

from ..helpers import BaseApplicationTest
from ..helpers import LoggedInApplicationTest


class TestSession(BaseApplicationTest):
    def test_index(self):
        response = self.client.get('/admin/')
        self.assertEquals(302, response.status_code)

    def test_login(self):
        response = self.client.post('/admin/login', data=dict(
            username="admin",
            password="admin"
        ))
        self.assertEquals(302, response.status_code)
        self.assertEquals("/admin/", urlsplit(response.location).path)

        response = self.client.get('/admin/')
        self.assertEquals(200, response.status_code)

    def test_invalid_login(self):
        response = self.client.post('/admin/login', data=dict(
            username="admin",
            password="wrong"
        ))
        self.assertEquals(200, response.status_code)

        response = self.client.get('/admin/')
        self.assertEquals(302, response.status_code)
        self.assertEquals("/admin/login", urlsplit(response.location).path)


class TestApplication(LoggedInApplicationTest):
    def test_main_index(self):
        response = self.client.get('/admin/')
        self.assertEquals(200, response.status_code)

    def test_404(self):
        response = self.client.get('/admin/not-found')
        self.assertEquals(404, response.status_code)

    def test_index_is_404(self):
        response = self.client.get('/')
        self.assertEquals(404, response.status_code)


class TestServiceView(LoggedInApplicationTest):
    def test_service_response(self):
        self.service_loader.get.return_value = {}
        response = self.client.get('/admin/service/1')

        self.service_loader.get.assert_called_with('1')

        self.assertEquals(200, response.status_code)


class TestServiceEdit(LoggedInApplicationTest):
    def test_service_edit_documents_get_response(self):
        response = self.client.get('/admin/service/1/edit/documents')

        self.service_loader.get.assert_called_with('1')

        self.assertEquals(200, response.status_code)

    def test_service_edit_documents_empty_post(self):
        self.service_loader.get.return_value = {
            'id': 1,
            'supplierId': 2,
        }
        response = self.client.post(
            '/admin/service/1/edit/documents',
            data={}
        )

        self.service_loader.get.assert_called_with('1')
        self.assertFalse(self.service_loader.post.called)

        self.assertEquals(302, response.status_code)
        self.assertEquals("/admin/service/1", urlsplit(response.location).path)

    def test_service_edit_documents_post(self):
        self.service_loader.get.return_value = {
            'id': 1,
            'supplierId': 2,
            'pricingDocumentURL': "http://assets/documents/1/2-pricing.pdf",
            'serviceDefinitionDocumentURL': "http://assets/documents/1/2-service-definition.pdf",  # noqa
            'termsAndConditionsDocumentURL': "http://assets/documents/1/2-terms-and-conditions.pdf",  # noqa
            'sfiaRateDocumentURL': None
        }
        response = self.client.post(
            '/admin/service/1/edit/documents',
            data={
                'serviceDefinitionDocumentURL': (StringIO(), ''),
                'pricingDocumentURL': (StringIO(b"doc"), 'test.pdf'),
                'sfiaRateDocumentURL': (StringIO(b"doc"), 'test.pdf'),
                'termsAndConditionsDocumentURL': (StringIO(b''), ''),
            }
        )

        self.service_loader.get.assert_called_with('1')
        self.service_loader.post.assert_called_with(1, {
            'pricingDocumentURL': 'https://assets.test.digitalmarketplace.service.gov.uk/documents/2/1-pricing-document-2015-01-01-1200.pdf',  # noqa
            'sfiaRateDocumentURL': 'https://assets.test.digitalmarketplace.service.gov.uk/documents/2/1-sfia-rate-card-2015-01-01-1200.pdf',  # noqa
        }, 'admin', 'admin app')

        self.assertEquals(302, response.status_code)

    def test_service_edit_documents_post_with_validation_errors(self):
        self.service_loader.get.return_value = {
            'id': 1,
            'supplierId': 2,
            'serviceDefinitionDocumentURL': "http://assets/documents/1/2-service-definition.pdf",  # noqa
            'pricingDocumentURL': "http://assets/documents/1/2-pricing.pdf",
            'sfiaRateDocumentURL': None
        }
        response = self.client.post(
            '/admin/service/1/edit/documents',
            data={
                'serviceDefinitionDocumentURL': (StringIO(), ''),
                'pricingDocumentURL': (StringIO(b"doc"), 'test.pdf'),
                'sfiaRateDocumentURL': (StringIO(b"doc"), 'test.txt'),
                'termsAndConditionsDocumentURL': (StringIO(), 'test.pdf'),
            }
        )

        self.service_loader.get.assert_called_with('1')
        self.service_loader.post.assert_called_with(1, {
            'pricingDocumentURL': 'https://assets.test.digitalmarketplace.service.gov.uk/documents/2/1-pricing-document-2015-01-01-1200.pdf',  # noqa
        }, 'admin', 'admin app')

        self.assertIn(b'Your document is not in an open format', response.data)
        self.assertIn(b'This question requires an answer', response.data)
        self.assertEquals(200, response.status_code)

    def test_service_edit_when_API_returns_error(self):
        self.service_loader.get.return_value = {
            'id': 1,
            'supplierId': 2,
            'pricingDocumentURL': "http://assets/documents/1/2-pricing.pdf",
            'sfiaRateDocumentURL': None
        }
        self.service_loader.post.return_value.ok = False
        self.service_loader.post.return_value.content = 'API ERROR'
        response = self.client.post(
            '/admin/service/1/edit/documents',
            data={
                'pricingDocumentURL': (StringIO(b"doc"), 'test.pdf'),
                'sfiaRateDocumentURL': (StringIO(b"doc"), 'test.txt'),
                'termsAndConditionsDocumentURL': (StringIO(), 'test.pdf'),
            }
        )
        self.assertIn(b'API ERROR', response.data)