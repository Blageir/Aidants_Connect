from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import tag
from selenium.webdriver.firefox.webdriver import WebDriver
from aidants_connect_web.models import Aidant, Usager, Mandat
from datetime import date


@tag("functional")
class ViewMandats(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        cls.user = Aidant.objects.create_user(
            username="Thierry",
            email="thierry@thierry.com",
            password="motdepassedethierry",
            first_name="Thierry",
            last_name="Martin",
        )
        cls.usager = Usager.objects.create(
            given_name="Joséphine",
            family_name="ST-PIERRE",
            preferred_username="ST-PIERRE",
            birthdate=date(1969, 12, 25),
            gender="female",
            birthplace=70447,
            birthcountry=99100,
            sub="test_sub",
            email="Aidant@user.domain",
        )
        cls.usager2 = Usager.objects.create(
            given_name="Corentin",
            family_name="DUPUIS",
            preferred_username="DUPUIS",
            birthdate=date(1983, 2, 3),
            gender="male",
            birthplace=70447,
            birthcountry=99100,
            sub="test_sub2",
            email="Aidant2@user.domain",
        )
        cls.mandat = Mandat.objects.create(
            aidant=Aidant.objects.get(username="Thierry"),
            usager=Usager.objects.get(sub="test_sub"),
            demarche=["social"],
            duration=1,
        )
        cls.mandat2 = Mandat.objects.create(
            aidant=Aidant.objects.get(username="Thierry"),
            usager=Usager.objects.get(sub="test_sub"),
            demarche=["papiers"],
            duration=1,
        )
        cls.mandat3 = Mandat.objects.create(
            aidant=Aidant.objects.get(username="Thierry"),
            usager=Usager.objects.get(sub="test_sub2"),
            demarche=["famille"],
            duration=365,
        )
        super().setUpClass()
        cls.selenium = WebDriver()
        cls.selenium.implicitly_wait(10)
        cls.selenium.get(f"{cls.live_server_url}/dashboard/")

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super().tearDownClass()

    def test_grouped_mandats(self):
        self.selenium.get(f"{self.live_server_url}/dashboard/")

        # Login
        login_field = self.selenium.find_element_by_id("id_username")
        login_field.send_keys("Thierry")
        password_field = self.selenium.find_element_by_id("id_password")
        password_field.send_keys("motdepassedethierry")
        submit_button = self.selenium.find_element_by_xpath('//input[@value="Login"]')
        submit_button.click()

        # Dashboard
        self.selenium.find_element_by_id("view_mandats").click()

        # Mandat List
        self.assertEqual(len(self.selenium.find_elements_by_class_name("usager")), 2)
        rows = self.selenium.find_elements_by_tag_name("tr")
        # The first row is the title row
        mandats = rows[1:]
        self.assertEqual(len(mandats), 3)