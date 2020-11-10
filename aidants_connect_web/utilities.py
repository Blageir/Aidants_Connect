import io
import hashlib
import logging
import qrcode
from pathlib import Path

from django.conf import settings

logging.basicConfig(level=logging.INFO)
log = logging.getLogger()


def generate_sha256_hash(value: bytes):
    """
    Generate a SHA-256 hash
    https://docs.python.org/3/library/hashlib.html
    SHA-256 is a hash function that takes bytes as input, and returns a hash
    The length of the hash is 64 characters
    To add a salt, concatenate the string with the salt ('string'+'salt')
    You must encode your string to bytes beforehand ('stringsalt'.encode())
    :param value: bytes
    :return: a hash (string) of 64 characters
    """
    return hashlib.sha256(value).hexdigest()


def generate_file_sha256_hash(filename):
    """
    Generate a SHA-256 hash of a file
    """
    base_path = Path(__file__).resolve().parent
    file_path = (base_path / filename).resolve()
    with open(file_path, "rb") as f:
        file_bytes = f.read()  # read entire file as bytes
        file_readable_hash = generate_sha256_hash(file_bytes)
        return file_readable_hash


def validate_attestation_hash(attestation_string, attestation_hash):
    attestation_string_with_salt = attestation_string + settings.ATTESTATION_SALT
    new_attestation_hash = generate_sha256_hash(
        attestation_string_with_salt.encode("utf-8")
    )
    return new_attestation_hash == attestation_hash


def generate_qrcode_png(string: str):
    stream = io.BytesIO()
    img = qrcode.make(string)
    img.save(stream, "PNG")
    return stream.getvalue()


def check_request_parameters(
    parameters: dict, expected_static_parameters: dict, view_name: str
) -> tuple:
    """
    When a request arrives, this function checks that all requested parameters are
    present (if not, returns (1, "missing parameter") and if the static parameters are
    correct (if not, returns (1, "forbidden parameter value")). If all is good, returns
    (0, "all is good")
    :param parameters: dict of all parameters expected in the request
    (None if the parameter was not present)
    :param expected_static_parameters: subset of parameters that are not dynamic
    :param view_name: str with the name of the view for logging purposes
    :return: tuple (error, message) where error is a bool and message an str
    """
    for parameter, value in parameters.items():
        if not value:
            error_message = f"400 Bad request: There is no {parameter} @ {view_name}"
            log.info(error_message)
            return 1, "missing parameter"
        elif (
            parameter not in expected_static_parameters
            and parameter in ["state", "nonce"]
            and not value.isalnum()
        ):
            error_message = (
                f"403 forbidden request: malformed {parameter} @ {view_name}"
            )
            log.info(error_message)
            return 1, "malformed parameter value"
        elif (
            parameter in expected_static_parameters
            and value != expected_static_parameters[parameter]
        ):
            error_message = (
                f"403 forbidden request: unexpected {parameter} @ {view_name}"
            )
            log.info(error_message)
            return 1, "forbidden parameter value"
    return 0, "all good"
