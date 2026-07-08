# api/tests/test_security_headers.py
import pytest
from django.urls import reverse
from rest_framework import status

# Ensure the test suite interacts cleanly with the test database if required
pytestmark = pytest.mark.django_db


@pytest.fixture
def api_client():
    """Provides an unauthenticated Django test client instance."""
    from django.test import Client
    return Client()


@pytest.mark.parametrize(
    "route_name, expected_status",
    [
        ("api-v1-scan-list", status.HTTP_200_OK),  # Update with your actual URL names
        ("api-v1-dashboard-summary", status.HTTP_200_OK),
    ]
)
def test_production_security_headers_are_present(api_client, route_name, expected_status):
    """
    Asserts that the application includes vital security headers (HSTS, CSP, CORS)
    in the HTTP response to defend against XSS, Man-in-the-Middle, and hijacking attacks.
    """
    # Arrange
    url = reverse(route_name)

    # Act
    # Enforce secure HTTPS connection flags on the request to trigger HSTS processing
    response = api_client.get(url, SECURE=True, HTTP_X_FORWARDED_PROTO="https")

    # Assert
    assert response.status_code == expected_status

    # 1. Validate HSTS (HTTP Strict Transport Security)
    assert "Strict-Transport-Security" in response, "HSTS header is missing entirely."
    hsts_header = response["Strict-Transport-Security"]
    assert "max-age=31536000" in hsts_header, "HSTS max-age is not set to standard 1 year minimum."
    assert "includeSubDomains" in hsts_header, "HSTS directive is missing includeSubDomains."
    assert "preload" in hsts_header, "HSTS directive is missing preload registration."

    # 2. Validate CSP (Content Security Policy)
    assert "Content-Security-Policy" in response, "Content-Security-Policy header is missing entirely."
    csp_header = response["Content-Security-Policy"]
    assert "default-src 'self'" in csp_header, "CSP policy does not fallback to secure 'self' boundaries."

    # 3. Validate Basic XSS and Framing Protections
    assert "X-Frame-Options" in response, "X-Frame-Options is missing."
    assert response["X-Frame-Options"] == "DENY", "Clickjacking mitigation not set to DENY."

    assert "X-Content-Type-Options" in response, "X-Content-Type-Options is missing."
    assert response["X-Content-Type-Options"] == "nosniff", "MIME-sniffing mitigation is disabled."


def test_cors_preflight_options_request(api_client):
    """
    Verifies that the application handles cross-origin preflight checks correctly,
    restricting origin access strictly to trusted domains.
    """
    # Arrange
    url = reverse("api-v1-scan-list")
    trusted_origin = "https://internal-dashboard.tesco.org"

    # Act: Fire an OPTIONS request mimicking a browser preflight mechanism
    response = api_client.options(
        url,
        HTTP_ORIGIN=trusted_origin,
        HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST"
    )

    # Assert
    assert response.status_code in [status.HTTP_200_OK, status.HTTP_204_NO_CONTENT]
    assert "Access-Control-Allow-Origin" in response, "CORS origin validation header missing."
    assert response[
               "Access-Control-Allow-Origin"] == trusted_origin, f"CORS failed to explicitly trust {trusted_origin}."
