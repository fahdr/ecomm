"""
Re-export shared ApiKey model from ecomm_core.

For Developers:
    Import ApiKey from here or directly from ecomm_core.models.
"""

from ecomm_core.models.api_key import ApiKey

__all__ = ["ApiKey"]
