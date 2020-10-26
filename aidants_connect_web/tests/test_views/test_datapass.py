from django.test import tag, TestCase
from aidants_connect_web.views import datapass
from django.urls import resolve


@tag("datapass")
class Datapass(TestCase):
    def setUp(self):
        pass

    def test_datapass_receiver_url_triggers_the_receiver_view(self):
        found = resolve("/datapass_receiver/")
        self.assertEqual(found.func, datapass.receiver)

    def test_bad_authorization_header_triggers_403(self):
        response = self.client.get(
            "/datapass_receiver/", **{"HTTP_AUTHORIZATION": "bad_token"}
        )
        self.assertEqual(response.status_code, 403)

    def test_good_authorization_header_triggers_200(self):
        response = self.client.get(
            "/datapass_receiver/", **{"HTTP_AUTHORIZATION": "good_token"}
        )
        self.assertEqual(response.status_code, 202)

    # def test_message_body_can_create_organisation(self):
    #     response = self.client.get(
    #         "/datapass_receiver/", **{"HTTP_AUTHORIZATION": "good_token"},
    #         data={
    #             "name": "name",
    #             "email": "email",
    #             "data_pass_id": "id",
    #             "scopes": "scopes",
    #             "organisation_name": "organisation_name",
    #             "siret" : "siret",
    #           }
    #     )
