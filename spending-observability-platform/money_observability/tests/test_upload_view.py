from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse


class UploadCSVViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="testuser", password="testpass")
        self.url = reverse("upload_csv")

    def _csv(self, name="statement.csv", content=b"Date,Description,Amount\n01/01/2026,Coffee,10.00"):
        return SimpleUploadedFile(name, content, content_type="text/csv")

    # --- auth ---

    def test_get_redirects_unauthenticated(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        self.assertIn("/admin/login/", response["Location"])

    # --- GET ---

    def test_get_renders_upload_form(self):
        self.client.force_login(self.user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="csv_files"')

    # --- POST: valid upload ---

    def test_post_valid_csv_shows_success_message(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {"csv_files": self._csv()}, follow=True)
        self.assertEqual(response.status_code, 200)
        messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("statement.csv" in m for m in messages))
        self.assertTrue(any("Processed" in m for m in messages))

    def test_post_valid_csv_reports_row_count(self):
        self.client.force_login(self.user)
        content = b"Date,Description,Amount\n01/01/2026,Coffee,10.00\n02/01/2026,Tea,5.00\n"
        response = self.client.post(self.url, {"csv_files": self._csv(content=content)}, follow=True)
        messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("2 transaction" in m for m in messages))

    def test_post_multiple_csv_files_shows_success_for_each(self):
        self.client.force_login(self.user)
        files = [self._csv("a.csv"), self._csv("b.csv")]
        response = self.client.post(self.url, {"csv_files": files}, follow=True)
        messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("2 file(s)" in m for m in messages))

    # --- POST: invalid input ---

    def test_post_no_files_shows_error(self):
        self.client.force_login(self.user)
        response = self.client.post(self.url, {}, follow=True)
        messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("No files selected" in m for m in messages))

    def test_post_non_csv_file_shows_error(self):
        self.client.force_login(self.user)
        bad_file = SimpleUploadedFile("report.xlsx", b"data", content_type="application/octet-stream")
        response = self.client.post(self.url, {"csv_files": bad_file}, follow=True)
        messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("report.xlsx" in m for m in messages))
        self.assertFalse(any("Processed" in m for m in messages))

    def test_post_mixed_files_accepts_csv_and_rejects_other(self):
        self.client.force_login(self.user)
        files = [self._csv("good.csv"), SimpleUploadedFile("bad.txt", b"x", content_type="text/plain")]
        response = self.client.post(self.url, {"csv_files": files}, follow=True)
        messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("good.csv" in m for m in messages))
        self.assertTrue(any("bad.txt" in m for m in messages))

    # --- POST: HSBC headerless format ---

    def test_post_hsbc_csv_detected_as_hsbc(self):
        self.client.force_login(self.user)
        content = (
            b'20/05/2026,CARTER JONAS LLP,"-2,100.00"\n'
            b"20/05/2026,AMERICAN EXPRESS DD,-446.29\n"
            b"19/05/2026,SOME MERCHANT,-28.00\n"
        )
        hsbc_file = SimpleUploadedFile("hsbc.csv", content, content_type="text/csv")
        response = self.client.post(self.url, {"csv_files": hsbc_file}, follow=True)
        msgs = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("hsbc" in m for m in msgs), msgs)
        self.assertTrue(any("3 transaction" in m for m in msgs), msgs)
