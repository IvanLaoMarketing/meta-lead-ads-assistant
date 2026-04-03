"""
utils/meta_api_client.py
Client centralizzato per Meta Marketing API.
Gestisce autenticazione, retry con backoff esponenziale e rate limiting.
"""

from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from facebook_business.exceptions import FacebookRequestError
from config.settings import settings
from utils.logger import get_logger

logger = get_logger("meta_api_client")


def init_meta_api():
    """Inizializza l'SDK Meta con le credenziali dal .env."""
    FacebookAdsApi.init(
        app_id=settings.meta_app_id,
        app_secret=settings.meta_app_secret,
        access_token=settings.meta_access_token
    )
    logger.info("[Meta API] SDK inizializzato correttamente.")


def get_ad_account() -> AdAccount:
    """Restituisce l'oggetto AdAccount configurato."""
    return AdAccount(settings.meta_ad_account_id)


@retry(
    retry=retry_if_exception_type(FacebookRequestError),
    wait=wait_exponential(multiplier=2, min=4, max=60),
    stop=stop_after_attempt(5)
)
def safe_meta_call(func, *args, **kwargs):
    """
    Wrapper con retry automatico per chiamate API Meta.
    Gestisce rate limit (errore 17) e errori transitori.

    Uso:
        result = safe_meta_call(campaign.remote_create)
    """
    try:
        return func(*args, **kwargs)
    except FacebookRequestError as e:
        if e.api_error_code() == 17:
            logger.warning(f"[Meta API] Rate limit raggiunto. Retry in corso...")
        else:
            logger.error(f"[Meta API] Errore {e.api_error_code()}: {e.api_error_message()}")
        raise
